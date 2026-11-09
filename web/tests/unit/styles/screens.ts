/**
 * The rendered screens the contrast census is taken over.
 *
 * The census is only as wide as what it renders, so this file is deliberately the widest
 * set of real components this suite can produce in one server pass: every page, every
 * widget, and — the part that matters — every widget in the STATES that put a different
 * ink on a different tint. A badge in five tones, a state panel in error and in warning,
 * a finding row selected and not, a quotation whose anchor disagrees, a disabled control,
 * an export that has already produced a file. A census taken over resting screens alone
 * would have missed `ink-soft` on `accent-light` and `ink-soft` on `failed-light`, which
 * are two of the failures this wave repaired.
 *
 * Nothing here is new machinery: it renders with `tests/unit/screens/harness.ts` and the
 * fixtures `tests/unit/review` already uses, and adds no dependency.
 */

import { createElement } from 'react';
import type { ComponentType, ReactElement } from 'react';

import { HomePage } from '@/_pages/home';
import { ProjectsPage } from '@/_pages/projects';
import { FindingBlocksStrip, PageBlocksStrip, ReviewFindingBlocks, ReviewPage, ReviewPageBlocks, ReviewViewerAside, ReviewViewerDialog } from '@/_pages/review';
import { VersionDetailPage } from '@/_pages/version-detail';
import { StageComparisonPage } from '@/_pages/stage-comparison';
import { AppFrame } from '@/_app';
import { accountMenuProps } from '@/_app/account-menu';
import { MarkFaultView, UpdateBannerView, WhatsNewView } from '@/_app/release-notices';
import { FrameNavigationView } from '@/_app/frame-navigation';
import { menuBadgesOf } from '@/_app/menu-badges';
import { buildNavigation } from '@/_app/navigation';
import { sectionNavigationOf } from '@/_app/section-navigation';
import { ChangePasswordPage } from '@/_pages/change-password';
import { SignInPage } from '@/_pages/sign-in';
import { ManageUserControls } from '@/features/manage-user';
import { AuthEventList } from '@/widgets/auth-event-list';
import { UserCard } from '@/widgets/user-card';
import { UserList } from '@/widgets/user-list';
import { AdminAreaTabsView } from '@/entities/user';
import { RegistrationQueue } from '@/widgets/registration-queue';
import { VersionHistoryView } from '@/widgets/version-history';
import { KnowledgeBase } from '@/widgets/knowledge-base';
import { Dashboard } from '@/widgets/dashboard';
import { DecisionHistory } from '@/widgets/decision-history';
import { DecisionPanel } from '@/widgets/decision-panel';
import { DocumentList } from '@/widgets/document-list';
import { DocumentViewerView, EvidenceViewer, QuotationCard } from '@/widgets/evidence-viewer';
import { PageViewerView } from '@/features/open-evidence';
import type { PageViewerViewProps, Placement } from '@/features/open-evidence';
import { fitView, focusView, makeStage } from '@/features/open-evidence/model/view-state';
import { ExecutionJournal, JournalControls, RunPicker } from '@/widgets/execution-journal';
import { ExecutionQueue, QueueStateStrip } from '@/widgets/execution-queue';
import { WorkerList, WorkersOverviewSections, WorkersOverviewView } from '@/widgets/worker-list';
import { ExecutorConnections } from '@/widgets/executor-connections';
import { ExecutorRoutes } from '@/widgets/executor-routes';
import { WorkersPage } from '@/_pages/workers';
import { SectionFilterBar, SectionOptimisationPage, readSectionOptimisationAddress } from '@/_pages/section-optimisation';
import { ReviseConnectionForm } from '@/features/manage-executor-connection';
import { SetExecutorSecretForm } from '@/features/set-executor-secret';
import { AnalysisProfileTable } from '@/widgets/analysis-profile-table';
import { ArV3BetaReview } from '@/widgets/ar-v3-beta-review';
import { ArV3BetaPack } from '@/widgets/ar-v3-beta-pack';
import { StartArV3GroupView, classifyArV3GroupStartFailure } from '@/features/start-ar-v3-group';
import { SpecificationPricesAnswer, SpecificationPricesChooser } from '@/widgets/specification-prices';
import { OptimisationByDocument, ProposalSetChooser } from '@/widgets/optimisation-proposals';
import { VersionComparison } from '@/widgets/version-comparison';
import { NormReferencesAnswer } from '@/widgets/norm-references';
import { SectionSpecificationAnswer } from '@/widgets/section-specification';
import { SectionAcceptedList } from '@/widgets/section-accepted-optimisations';
import { NormSearchResults } from '@/widgets/norm-search';
import { NormCatalogueTable } from '@/widgets/norm-catalogue';
import { NormDocumentFacts, NormParagraphList, NormPdf } from '@/widgets/norm-document';
import { NormSnapshotHistory, NormSnapshotList } from '@/widgets/norm-snapshots';
import { ExportPanel } from '@/widgets/export-panel';
import { ChangesPanelView, ComparisonViewerView, canShowOverlay, initialState, reduce, viewerGeometry } from '@/widgets/comparison-viewer';
import type { EvidenceState } from '@/widgets/comparison-viewer';
import { evidenceOf } from '@/entities/version-series';
import type { TileStatus, ViewerAction, ViewerContext } from '@/widgets/comparison-viewer';
import { FindingList, FindingRowActions } from '@/widgets/finding-list';
import { BatchStartPanelView } from '@/features/start-run';
import { DocumentLifecycleView, DocumentTagsView } from '@/features/manage-document';
import { ExecutionStatusControlView } from '@/features/set-execution-status';
import { ImportDecisionsView } from '@/features/import-decisions';
import { ProposalDecisions } from '@/widgets/proposal-journal';
import { ProjectSections } from '@/widgets/project-sections';
import { SectionDetailPage } from '@/_pages/section-detail';
import { ProjectDetailPage } from '@/_pages/project-detail';
import { DocumentDetailPage } from '@/_pages/document-detail';
import { WorkScheduleMonthView } from '@/widgets/work-schedule-month';
import { ReserveCalendarView } from '@/widgets/reserve-calendar';
import { NO_ENGINEER_FILTER } from '@/entities/work-schedule';
import { assignmentUid, monthFixture, reserveFixture, EXPERT_A, EXPERT_B } from '../work-schedule/fixtures';
import { DocumentCardGrid } from '@/entities/document-version';
import type { BatchEstimate, BatchOutcome } from '@/features/start-run';
import { costEstimate } from '../analysis-settings/cost-estimate-fixtures';
import { ProjectList } from '@/widgets/project-list';
import { RunList } from '@/widgets/run-list';
import { RunProgress } from '@/widgets/run-progress';
import { UploadPanel } from '@/widgets/upload-panel';
import { DocumentContext, SectionNeighboursView, VersionTabsView, versionTabs } from '@/widgets/document-context';
import { VersionList } from '@/widgets/version-list';
import { BlockImageFailure, CropFigureView, PortalBlockCard, PortalBlockListView, findingsByBlock, findingsByPage } from '@/widgets/portal-blocks';
import type { PageFindingsReading } from '@/widgets/portal-blocks';
import { DocumentChooser, VersionBlockViews } from '@/_pages/blocks';
import { ClassifyVersionFormView } from '@/features/classify-version';
import { CorrectVersionClassificationFormView } from '@/features/correct-version-classification';
import { ProjectStructureView, sectionFigures } from '@/widgets/project-sections';
import { VersionClassificationView } from '@/widgets/version-classification';
import { findingBlockIndex, portalBlocksQueryOptions } from '@/entities/block';
import type {
  DashboardSummary,
  DecisionEvent,
  DecisionRecord,
  ErrorCode,
  ErrorEnvelope,
  Finding,
  NormCitation,
  RunState,
  RunStatus,
} from '@/shared/api';
import type { DocumentVersion, Project, SectionReview, Verdict } from '@/shared/api';
import type { Account, AnalysisPreset, AnalysisProfileListItem } from '@/shared/api';
import type { RegistrationRequest } from '@/shared/api';
import { ApiError, PROJECT_SECTION_VALUES, RUN_STATE_VALUES, queryKeys } from '@/shared/api';
import { routes } from '@/shared/lib';
import { AVATAR_PALETTE_SIZE, Avatar, Disclosure, ErrorState, LoadingState, Menu, avatarColourIndex, Table } from '@/shared/ui';
import type { DisclosureProps, MenuProps } from '@/shared/ui';
import { DisclosureView } from '@/shared/ui/disclosure';
import { MenuView } from '@/shared/ui/menu';
import { groupByCategory } from '@/entities/finding';
import { PROJECT_PAGE_LIMIT, PROJECT_SECTIONS } from '@/entities/project';
import { ProjectSwitcherView, buildSwitcherModel, switcherListOf } from '@/widgets/project-switcher';
import { PauseStatusView } from '@/widgets/pause-status';
import { UpdateTime, WORKER_PAGE_LIMIT } from '@/entities/execution';
import {
  CLASSIFY_NOT_PERMITTED_DETAIL,
  DOCUMENT_PAGE_LIMIT,
  VERSION_PAGE_LIMIT,
} from '@/entities/document-version';
import type { StageRow } from '@/entities/audit-run';
import { AR_V3_BETA_PROFILE_ID, RUN_PAGE_LIMIT, StageTable } from '@/entities/audit-run';

import {
  DOCUMENT_UID,
  FINDING_UID,
  OBSERVATION_ID,
  PROJECT_UID,
  RUN_ID,
  VERSION_UID,
  decisionEvent,
  evidence,
  finding,
  findingDetail,
  observation,
  render,
  runStatus,
} from '../review/fixtures';
import { addedPair, comparedPair } from '../comparison/viewer/viewer-fixtures';
import { description as aiDescription } from '../version-compare/ai-fixtures';
import { COMPARISON_SHAPES, panelProps } from '../version-compare/shapes';
import { newClient, renderScreen, renderWith, seedError } from '../screens/harness';
import {
  ADMIN as HOME_ADMIN, EXPERT as HOME_EXPERT, LABEL as HOME_LABEL, PROJECTS as HOME_PROJECTS, loaded as loadedHome, projectPage as homeProjectPage,
} from '../screens/home-fixtures';
import { derivedScreens, malformedVariants, wellFormed } from '../screens/route-screens';
import {
  NORM_CATALOGUE_ITEMS, NORM_CATALOGUE_PAGE, NORM_DOCUMENT_ID, NORM_EVENTS, NORM_HITS, NORM_PARAGRAPHS, NORM_SNAPSHOTS,
  normDocument,
} from '../norms/fixtures';
import { NormsPage, NormDocumentPage } from '@/_pages/norms';
import {
  NORM_CATALOGUE_PAGE_LIMIT, NORM_EVENT_PAGE_LIMIT, NORM_PARAGRAPH_PAGE_LIMIT, NORM_SEARCH_PAGE_LIMIT, NORM_SNAPSHOT_LIMIT,
} from '@/entities/norms';
import { ExecutorGroups } from '@/widgets/executor-groups';
import { ExecutorRules } from '@/widgets/executor-rules';
import { AnalysisPresets } from '@/widgets/analysis-presets';
import { ANALYSIS_PRESETS_KEY } from '@/entities/analysis-preset';
import {
  ARCHIVED_GROUP, MAIN_GROUP, ROUTED_GROUP, ruleOf, seedGroups, seedRules,
} from '../executor-groups/executor-groups-fixtures';
import {
  AgentSetup, ConnectWizard, EnrollmentCommandView, OpenRouterKeyStep, OpenRouterSetup, SshInstallForm,
} from '@/features/connect-remote-agent';
import { IssuedTokenView, RunnerTokenPanel } from '@/features/manage-executor-connection';
import { CutOverPreviewTable, GroupForm } from '@/features/manage-executor-group';
import { memberCandidates } from '@/entities/executor-group';
import { AnalysisSettingsPage } from '@/_pages/analysis-settings';
import { PROJECT_STRUCTURE_ORDER, projectSectionOf } from '@/entities/project';
import { CONNECTION_CASES, PREVIEW as CUT_OVER_PREVIEW } from '../executor-groups/executor-groups-fixtures';
import { issued as issuedEnrollment } from '../workers/connect-remote-agent-fixtures';
import { PULL_ONLINE } from '../workers/executor-fixtures';

import {
  BLOCKS_PROJECT_UID, BLOCKS_RUN_ID, BLOCKS_VERSION_UID, blockId, blocksOnFivePages, blocksVersion, everyKindOfBlock,
  imageBlock, portalPage, runFindings, stampBlock, textBlock,
} from '../blocks/fixtures';

import { optimisationShapes, seedLoadedOptimisation } from '../optimisation/fixtures';
import {
  ALL_CASES as EXECUTOR_CASES, PINNED as EXECUTOR_PINNED, READY as EXECUTOR_READY, seedExecutors,
} from '../workers/executor-fixtures';
import { carryOverShapes, proposalShapes, seedLoadedProposals } from '../optimisation-proposals/fixtures';
import { SECTION_NO_ROWS, sectionAnswer } from '../section-specification/fixtures';
import { ACCEPTED_PROJECT_A, acceptedPage } from '../section-optimisation/fixtures';
import {
  AVAILABLE_RUN_ID, GROUP_ID, accountFixture, groupReviewFixture, runFindingsPage, v3FindingFixture,
} from '../analysis-settings/ar-v3-beta-review-fixtures';
import {
  NOT_INSTALLED_PACK, installedPackFixture, withoutMember,
} from '../analysis-settings/ar-v3-beta-pack-fixtures';

import type { Screen } from './contrast';
import { auditCounts, sectionAudit } from '../dashboard/audit-counts';
import { QUEUE_WORK } from '../execution/queue-work';

function withRouter(element: ReactElement): string {
  return renderScreen(newClient(), element);
}

function apiError(status: number, code: ErrorCode, retryable: boolean): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.42.0',
    error_code: code,
    message: 'Одна безопасная для вызывающей стороны фраза.',
    correlation_id: 'cid-contrast-1',
    retryable,
  };
  return new ApiError(status, envelope, 'cid-contrast-1');
}

const noop = (): void => {};

/** The four identities this census uses, keyed as `web/src/app`'s directories spell them. */
const IDENTITIES = {
  projectUid: PROJECT_UID,
  documentUid: DOCUMENT_UID,
  versionUid: VERSION_UID,
  runId: RUN_ID,
};
const IDENTITY_SEGMENTS = wellFormed(IDENTITIES);

/** A seeded run screen in a given terminal outcome. */
function runScreen(state: RunState, overrides: Partial<RunStatus> = {}): string {
  const client = newClient();
  const status = runStatus({ run_id: RUN_ID, state, ...overrides });
  client.setQueryData(queryKeys.runs.detail(RUN_ID), status);
  return renderWith(
    client,
    createElement(RunProgress, { projectUid: PROJECT_UID, runId: RUN_ID }),
  );
}

const FINDINGS: readonly Finding[] = [
  finding({ finding_uid: FINDING_UID, category: 'internal_contradiction' }),
  finding({ finding_uid: `${FINDING_UID.slice(0, -1)}C`, category: 'explicit_placeholder' }),
];

const SHA = '6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f';

const project = (): Project => ({
  project_uid: PROJECT_UID,
  name: 'Договор поставки',
  created_at: '2026-09-10T08:00:00.000Z',
  document_count: 2,
  // `UI-A-10`, `UI-A-35`: the counters `listProjects` and `getProject` carry, so the list row and the project's figures are drawn.
  audit_counts: auditCounts(6, { not_run: 2, awaiting_decision: 2, checked: 1, clean: 1, no_expert_decision: 4 }),
});

const version = (): DocumentVersion => ({
  version_uid: VERSION_UID,
  document_uid: DOCUMENT_UID,
  project_uid: PROJECT_UID,
  version_ordinal: 1,
  media_type: 'application/pdf',
  byte_size: 58978,
  sha256: SHA,
  page_count: 8,
  published_at: '2026-09-18T06:55:52.642022Z',
  input_manifest: [
    { role: 'source.document', media_type: 'application/pdf', sha256: SHA, size_bytes: 58978 },
  ],
  display_title: 'Годовой отчёт',
  source_filename: 'отчёт.pdf',
});

/**
 * `W59-SECTION-UI-01`. One version's section review: unconfirmed, one section suggested with
 * evidence — so the expert's form renders every part it has.
 *
 * `PB-PROFILE-01`: every section has a registered profile now (ПБ has a draft one), so the API's
 * answer marks all fifteen options executable and so does this fixture.
 * `sectionReviewWithoutProfile` is the other answer the contract allows, from a server whose
 * registry lacks `UNPROFILED`'s profile: it keeps the census reaching the «профиль анализа
 * недоступен» states without naming a real section that is in fact profile-less.
 */
const sectionReview = (over: Partial<SectionReview> = {}): SectionReview => ({
  version_uid: VERSION_UID,
  classification: null,
  revisions: [],
  recognised_text_consulted: false,
  options: PROJECT_SECTION_VALUES.map((code) => ({
    section_code: code,
    name: code,
    executable: true,
    suggestion:
      code === 'AR'
        ? { score: 5, filename_patterns: ['АР'], text_keywords: ['фасад'], name_in_text: true }
        : null,
  })),
  ...over,
});

/** A section the stand's registry is imagined to lack; any of the fifteen could be, ГП stands for it. */
const UNPROFILED = 'GP' as const;

const sectionReviewWithoutProfile = (over: Partial<SectionReview> = {}): SectionReview => {
  const review = sectionReview(over);
  return {
    ...review,
    options: review.options.map((option) => ({
      ...option,
      executable: option.section_code !== UNPROFILED,
    })),
  };
};

const CONFIRMED = {
  version_uid: VERSION_UID,
  project_stage: 'R' as const,
  section_code: UNPROFILED,
  confirmed_at: '2026-10-20T08:00:00Z',
  confirmed_by_user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
  revision: 1,
};

/**
 * A client whose four lists have ROWS IN THEM, and a next page.
 *
 * Every list in this census was cold, so `li.am-state` -- the class every project row and
 * every run row carries -- was reached by no screen, and with it the whole populated-list
 * surface and the pager. `W41-BLIND` found that by asking which colour-bearing rules no
 * screen reaches. The lists had been in the census by name since wave 32 and in a state
 * that renders a spinner.
 */
function populatedClient() {
  const client = newClient();
  const page = { next_cursor: 'Y3Vyc29y' } as { next_cursor: string };
  client.setQueryData(queryKeys.projects.list(undefined, PROJECT_PAGE_LIMIT), { items: [project()], page });
  client.setQueryData(queryKeys.projects.detail(PROJECT_UID), project());
  client.setQueryData(queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT), { items: [version()], page });
  // `UI-PARITY-DOC-AUDIT`: the project screen reads the listing in the server's audit order, an entry of its own.
  client.setQueryData(
    queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT, undefined, false, undefined, undefined, 'audit'),
    { items: [version()], page },
  );
  client.setQueryData(queryKeys.versions.list(DOCUMENT_UID, undefined, VERSION_PAGE_LIMIT), { items: [version()], page });
  client.setQueryData(queryKeys.versions.detail(VERSION_UID), version());
  client.setQueryData(queryKeys.versions.sectionReview(VERSION_UID), sectionReview());
  client.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), { items: [runStatus({ run_id: RUN_ID })], page });
  // `AR-V3-BETA-PACK-STATUS-WEB-01`: an installed reviewed pack, so every screen drawn from this
  // client that holds the run list also draws the six-check start and its separating rule.
  client.setQueryData(queryKeys.runs.arV3PackStatus(), installedPackFixture());
  // `diagnostic_observation_count` on purpose: the review header's diagnostics sentence
  // renders only above zero, and every fixture in this file left it at the default.
  client.setQueryData(
    queryKeys.runs.detail(RUN_ID),
    runStatus({ run_id: RUN_ID, diagnostic_observation_count: 1 }),
  );
  return client;
}

/** Journal rows for the knowledge base, one per verdict the contract publishes. */
const RECORDS: readonly DecisionRecord[] = (
  ['accepted', 'rejected', 'needs_manual_review', 'pending'] as const
).map((verdict, index) => ({
  ...decisionEvent({
    decision_id: `${decisionEvent().decision_id.slice(0, -1)}${'ABCD'[index] ?? 'A'}`,
    verdict,
    comment: 'Замечание проверяющего.',
  }),
  project_uid: PROJECT_UID,
  run_id: RUN_ID,
  document_uid: 'doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
  version_uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
  project_name: 'Школа',
  document_name: 'АР-1',
  category: index % 2 === 0 ? 'internal_contradiction' : 'explicit_placeholder',
  finding_text: 'Срок поставки указан как 30 дней в §4 и как 45 дней в §9.',
  current_verdict: verdict,
  decision_event_count: index + 1,
}));

/**
 * `WEB-REVIEW-FOLLOWUPS-01`: a v2 finding -- proposed severity, required and stated values, two
 * norm citations (one verified, one rebound) and a merged sibling -- and its decided severity.
 * Every string is Cyrillic, as the rest of this file seeds, so the language guards reading these
 * screens see only what the application wrote.
 */
const V2_CITATION = (over: Partial<NormCitation> = {}): NormCitation => ({
  clause_number: '7.1.4',
  designation: 'СП 1.13130.2020',
  norm_document_id: 'ndoc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
  norm_paragraph_id: 'npar_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
  norms_snapshot_id: 'ns_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
  page_label: 12,
  quote: 'Ширина эвакуационного выхода должна быть не менее 0,8 м.',
  source_attribution: 'consultant_plus',
  state: 'verified',
  title: 'Системы противопожарной защиты. Эвакуационные пути и выходы',
  ...over,
});

const V2_OBSERVATION = observation({
  finding_text: 'Ширина выхода указана как 0,7 м.',
  recommendation_text: 'Привести ширину выхода в соответствие с нормой.',
  evidence: [evidence({ quote: 'Ширина выхода — 0,7 м', page_number: 3 })],
  proposed_severity: 'critical',
  required_value: 'не менее 0,8 м',
  stated_value: '0,7 м',
  norm_citations: [V2_CITATION(), V2_CITATION({ state: 'rebound', clause_number: '7.1.5' })],
});

const V2_SIBLING = observation({
  finding_observation_id: 'fobs_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z',
  finding_text: 'Ширина эвакуационного выхода на плане — 0,7 м.',
  recommendation_text: 'Привести ширину выхода в соответствие с нормой.',
  evidence: [evidence({ quote: 'Выход шириной 0,7 м', page_number: 5 })],
  proposed_severity: 'economic',
});

/** One event per severity the contract publishes, an accept each, plus a comment that has none. */
const SEVERITY_EVENTS: readonly DecisionEvent[] = [
  ...(['critical', 'economic', 'operational', 'recommendation', 'check_adjacent'] as const).map(
    (severity, index) =>
      decisionEvent({
        decision_id: `${decisionEvent().decision_id.slice(0, -1)}${'ABCDE'[index] ?? 'A'}`,
        verdict: 'accepted',
        severity,
        recorded_at: `2026-09-10T09:0${index}:00.000Z`,
      }),
  ),
  decisionEvent({
    decision_id: `${decisionEvent().decision_id.slice(0, -1)}F`,
    event_type: 'comment',
    verdict: null,
    comment: 'Замечание проверяющего.',
    recorded_at: '2026-09-10T09:09:00.000Z',
  }),
];

/** The frame's sessions (`W50-SHELL-FRAME`): the whole subject the layout hands it. */
const FRAME_EXPERT = {
  login: 'эксперт@пример.испытание',
  displayLabel: 'Экспертова А. С.',
  initials: 'ЭА',
  roles: ['expert'],
  isDefaultCredential: false,
  profileComplete: true,
} as const;
const FRAME_ADMIN = { ...FRAME_EXPERT, displayLabel: 'Проверкина А. С.', initials: 'ПА', roles: ['admin', 'expert'] } as const;

const USER_ACCOUNT: Account = {
  archived_at: null,
  display_label: 'Проверкина А. С.',
  first_name: 'Анна',
  is_default_credential: false,
  last_name: 'Проверкина',
  last_sign_in_at: '2026-11-05T09:30:15Z',
  login: 'proverkina@example.org',
  middle_name: 'Сергеевна',
  profile_complete: true,
  roles: ['admin', 'expert'],
  user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
};

const REGISTRATION_REQUEST: RegistrationRequest = {
  created_user_uid: null,
  decided_at: null,
  decided_by: null,
  display_label: 'Заявкина М. П.',
  first_name: 'Мария',
  last_name: 'Заявкина',
  login: 'zayavkina@example.org',
  middle_name: 'Петровна',
  rejection_reason: null,
  request_id: 'reg_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
  status: 'pending',
  submitted_at: '2026-10-08T00:00:00Z',
};

/**
 * `CMP-VIEWER-01`: the sheet viewer, one static pass in the state a step list leaves it in. `tiles` says what has
 * arrived; the markup is {@link ComparisonViewerView}'s, which is what the reader gets.
 */
function comparisonViewerMarkup(
  pair: ReturnType<typeof comparedPair>,
  steps: ViewerAction[] = [],
  options: { tiles?: Partial<TileStatus>; dragging?: boolean; navigation?: boolean; evidence?: EvidenceState; sidePanel?: ReactElement } = {},
): string {
  const geometry = viewerGeometry(pair);
  const context: ViewerContext = {
    raster: geometry?.raster ?? { widthPx: 1, heightPx: 1 }, dpi: geometry?.dpi ?? 72, differences: pair.differences ?? [],
    canOverlay: canShowOverlay(pair), hasA: pair.page_a !== undefined, hasB: pair.page_b !== undefined,
  };
  let state = initialState(context, { width: 1000, height: 600 });
  for (const step of steps) state = reduce(state, step, context);
  const tiles: TileStatus = {
    urlOf: (request) => `blob:${request.mode}-${request.level}-${request.column}-${request.row}`,
    failed: 0, pending: 0, retry: noop, ...options.tiles,
  };
  return render(createElement(ComparisonViewerView, {
    pair, geometry, context, state, tiles, dispatch: noop, ...(options.dragging === true ? { dragging: true } : {}),
    ...(options.navigation === true ? { navigation: { onPrevious: noop, onNext: noop, onClose: noop } } : {}),
    ...(options.evidence === undefined ? {} : { evidence: options.evidence, onEvidence: noop }),
    ...(options.sidePanel === undefined ? {} : { sidePanel: options.sidePanel }),
  }));
}

export function screens(): Screen[] {
  const out: Screen[] = [];
  /**
   * A screen is wrapped in `<html><body>` before the census reads it, because `body` is
   * where the canvas background is declared and a fragment rendered on its own has none.
   * Without this, every element whose ancestors declare no background resolves to its OWN
   * background and a primary button reports its border against its own fill.
   */
  const add = (name: string, markup: string): void => {
    out.push({ name, markup: `<html><body>${markup}</body></html>` });
  };

  // ------------------------------------------------------------------- the shell
  add('AppFrame', render(createElement(AppFrame, { children: 'экран', session: null })));

  /*
   * `D-113`. The bar has two states and the census must see both: the signed-out half is a
   * link and the signed-in half is the submit control of a form. They carry the same class
   * -- `.am-app__signin` -- and a census that rendered only the link would be measuring the
   * rule on an `<a>` while a `<button>` somewhere else wore it.
   */
  add('AppFrame with an open session', render(createElement(AppFrame, { children: 'экран', session: FRAME_EXPERT })));

  /*
   * `W50-SHELL-FRAME`. The frame's islands render closed in one pass, so the states a reader
   * opens are seeded the way `W50-SHELL-UI`'s primitives are: the account menu OPEN with the
   * very props the bar gives it (`accountMenuProps`, not a copy), its header carrying the
   * frame's own rules; and the navigation drawn with every disclosure open — the one-row
   * groups and the stacked «Меню» with its inline groups — once with `Главная` as the current
   * page and once with a page under a group current, which is the only way the current-page
   * rules are reached by a pass that has no router.
   */
  {
    const inBar = (child: ReactElement): string => render(createElement('header', { className: 'am-app__bar' }, child));
    let seedPanel = 0;
    const drawnOpen = (props: DisclosureProps): ReactElement => {
      seedPanel += 1;
      return createElement(DisclosureView, { ...props, open: true, panelId: `seed-frame-${seedPanel}` });
    };
    add(
      'AppFrame, the account menu open',
      inBar(
        createElement(MenuView, {
          ...accountMenuProps(FRAME_ADMIN),
          state: { open: true, active: 0 },
          triggerId: 'seed-frame-account-trigger',
          menuId: 'seed-frame-account-menu',
        }),
      ),
    );
    /*
     * `R-150b`, `UI-PARITY-01` wave 1: the project selector OPEN, in the states it has, drawn in the
     * bar, with the props the widget gives `Menu` (`switcherMenuProps`, not a copy). A global screen draws the muted button with its hint; an optional one the named
     * project, the rows with their two figures, a long name, and the «показаны первые» note; a failed
     * read the alert, its detail and its correlation id, and the retry; a read in flight the status line.
     */
    {
      let seedSwitcher = 0;
      const switcherOpen = (props: MenuProps): ReactElement => {
        seedSwitcher += 1;
        return createElement(MenuView, {
          ...props,
          state: { open: true, active: 0 },
          triggerId: `seed-switcher-trigger-${seedSwitcher}`,
          menuId: `seed-switcher-menu-${seedSwitcher}`,
        });
      };
      // Drawn in the bar the way the account menu above is: the bar and the top strip share one palette scope
      // (`globals.css`), and a bare `.am-app__utility` would add its own border as a pair of its own.
      const inStrip = inBar;
      const SWITCHER_UID = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
      const counted = (uid: string, name: string, over: Partial<ReturnType<typeof auditCounts>> = {}): Project => ({
        project_uid: uid,
        name,
        created_at: '2026-11-03T09:30:00Z',
        audit_counts: auditCounts(6, { not_run: 2, awaiting_decision: 3, clean: 1, no_expert_decision: 5, ...over }),
      });
      const SWITCHER_PAGE = {
        items: [
          counted(SWITCHER_UID, 'Мост через Неву'),
          counted('prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8C', 'Д'.repeat(200), { not_run: 0, awaiting_decision: 0, checked: 6, no_expert_decision: 0 }),
          { project_uid: 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8D', name: 'Без счётчиков', created_at: '2026-11-03T09:30:00Z' },
        ],
        page: { next_cursor: 'cursor-next' },
      };
      const seeded = (pathname: string, search: string, data: typeof SWITCHER_PAGE | undefined, error: unknown): string =>
        inStrip(
          createElement(ProjectSwitcherView, {
            model: buildSwitcherModel({ pathname, searchParams: new URLSearchParams(search) }, switcherListOf(data, error)),
            onRetry: noop,
            menu: switcherOpen,
          }),
        );
      add(
        'AppFrame, the project selector open on an optional screen, the project named, rows and the first-page note',
        seeded('/dashboard', `project=${SWITCHER_UID}`, SWITCHER_PAGE, null),
      );
      // `D-363`: the ✓ of the project that is open, on the row with the 200-character name (the cell keeps its column while the name wraps).
      add(
        'AppFrame, the project selector open, the project with the long name marked current',
        seeded('/dashboard', 'project=prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8C', SWITCHER_PAGE, null),
      );
      add('AppFrame, the project selector open on a global screen, muted, the list loading', seeded('/queue', '', undefined, null));
      add(
        'AppFrame, the project selector open, the read failed',
        seeded('/dashboard', `project=${SWITCHER_UID}`, undefined, apiError(503, 'dependency_unavailable', true)),
      );
      add(
        'AppFrame, the project selector open, a refresh failed over a loaded list',
        seeded('/dashboard', '', SWITCHER_PAGE, apiError(503, 'dependency_unavailable', true)),
      );
      // `R-151f`: the queue's pause state in the strip -- paused with the switch asked and a refusal, and unread.
      const pauseView = (over: Partial<Parameters<typeof PauseStatusView>[0]>) => inStrip(createElement(PauseStatusView, {
        status: { paused: true, changed_at: '2026-11-05T10:00:00Z' }, failed: false, mayToggle: true, asking: true,
        busy: false, error: 'Недостаточно прав для этого действия.', onAsk: noop, onConfirm: noop, onCancel: noop, ...over,
      }));
      add('AppFrame, the pause state: paused, the switch asked, a refusal', pauseView({}));
      add('AppFrame, the pause state: unread', pauseView({ status: undefined, failed: true }));
    }
    add(
      'Release history, loading',
      render(createElement(VersionHistoryView, {
        version: null, listing: null, loading: true, error: null,
        onClose: () => undefined, onRetry: () => undefined,
      })),
    );
    add(
      'Web update banner',
      render(createElement(UpdateBannerView, { onUpdate: () => undefined, onLater: () => undefined })),
    );
    add('Release-note read fault', render(createElement(MarkFaultView)));
    add(
      'Whats New dialog',
      render(createElement(WhatsNewView, {
        newest: '0.3.0', onClose: () => undefined,
        listing: { whats_new: ['0.3.0'], items: [{
          version: '0.3.0', revision: 1, date: '2026-10-08', title: 'Новые возможности',
          is_archive: false, range_label: null,
          items: [{ kind: 'new', screen: 'home', where: 'Работа › Главная', text: 'Открыта история версий.' }],
        }] },
      })),
    );
    add(
      'Whats New dialog, two versions',
      render(createElement(WhatsNewView, {
        newest: '0.3.1', onClose: () => undefined,
        listing: { whats_new: ['0.3.1', '0.3.0'], items: [{
          version: '0.3.1', revision: 1, date: '2026-10-09', title: 'Небольшие улучшения',
          is_archive: false, range_label: null,
          items: [
            { kind: 'improved', screen: 'home', where: 'Работа › Главная', text: 'Плитки главной стали плотнее.' },
            { kind: 'fixed', screen: 'home', where: 'Работа › Главная', text: 'Счётчик на плитке больше не прыгает.' },
          ],
        }, {
          version: '0.3.0', revision: 1, date: '2026-10-08', title: 'Новые возможности',
          is_archive: false, range_label: null,
          items: [{ kind: 'new', screen: 'home', where: 'Работа › Главная', text: 'Открыта история версий.' }],
        }] },
      })),
    );
    add(
      'Release history, long item at narrow width',
      render(createElement(VersionHistoryView, {
        version: '0.3.0', loading: false, error: null,
        listing: { whats_new: [], items: [{
          version: '0.3.0', revision: 1, date: '2026-10-08', title: 'История улучшений',
          is_archive: false, range_label: null,
          items: [{ kind: 'improved', screen: 'home', where: 'Работа › Главная', text: 'Д'.repeat(400) }],
        }, {
          version: '0.2.0', revision: 1, date: '2026-10-01', title: 'Ранние изменения',
          is_archive: true, range_label: '0.1–0.2',
          items: [{ kind: 'fixed', screen: 'home', where: 'Работа › Главная', text: 'Исправлен вход.' }],
        }] },
        onClose: () => undefined, onRetry: () => undefined,
      })),
    );
    // `R-151m` took «Блоки» out of the menu; «Нормы» is the knowledge item drawn current.
    for (const pathname of ['/', '/norms']) {
      add(
        `AppFrame, the navigation open, ${pathname} current`,
        inBar(
          createElement(FrameNavigationView, {
            navigation: buildNavigation(FRAME_ADMIN),
            pathname,
            disclosure: drawnOpen,
          }),
        ),
      );
    }

    /*
     * `UI-A-04`: the current project's «Разделы» -- the mark with its count badge, the section page being shown current
     * (the `.sectionMark` and `.sectionCount` rules, and the hover/current rules of the links they sit in), and the
     * notes of a group that has no list yet (`.sectionNote`).
     */
    const sectionRows = PROJECT_SECTIONS.map((section) => {
      const documents = section.code === 'AR' ? 4 : section.code === 'KJ' ? 12 : 0;
      return { section: section.code, document_count: documents, ...sectionAudit(documents) };
    });
    const sectionPage = routes.projectSection(PROJECT_UID, 'KJ');
    for (const [label, sections] of [
      ['listed, КЖ current', sectionNavigationOf(sectionRows, PROJECT_UID, sectionPage)],
      ['loading', { status: 'loading' }],
      ['failed', { status: 'failed' }],
    ] as const) {
      add(
        `AppFrame, the navigation open, the project's sections ${label}`,
        inBar(
          createElement(FrameNavigationView, {
            navigation: buildNavigation(FRAME_ADMIN),
            pathname: sectionPage,
            projectUid: PROJECT_UID,
            sections,
            disclosure: drawnOpen,
          }),
        ),
      );
    }

    /*
     * `UI-A-05`, `UI-A-06`, `UI-A-91`: the counters beside the items -- the section's red number of documents no expert has
     * checked next to its count (and the same sum on the «Разделы» group's own button, `D-360`), and the pills of «Очередь», «База знаний» and «Заявки на регистрацию» in the bar, on the
     * rail's glyphs and in the stacked menu (`.itemBadges`, `.badge`, `.badgeCount`, `.badgeAlert`, `.railBadges`). One
     * figure is past two digits, so the `99+` form is measured too.
     */
    const waitingRows = PROJECT_SECTIONS.map((section) => {
      const documents = section.code === 'AR' ? 4 : section.code === 'KJ' ? 120 : 0;
      const waiting = section.code === 'AR' ? 3 : section.code === 'KJ' ? 120 : 0;
      return { section: section.code, document_count: documents, ...sectionAudit(documents, { awaiting_decision: waiting }) };
    });
    add(
      'AppFrame, the navigation open, the counters beside the items and the sections\' red number',
      inBar(
        createElement(FrameNavigationView, {
          navigation: buildNavigation(FRAME_ADMIN),
          pathname: sectionPage,
          projectUid: PROJECT_UID,
          sections: sectionNavigationOf(waitingRows, PROJECT_UID, sectionPage),
          badges: menuBadgesOf({
            queueOverview: [{ state: 'queued', count: 2 }, { state: 'running', count: 1 }],
            // `D-331`: the red mark beside the count on «Очередь».
            queueRecentOverview: [{ state: 'failed', count: 2 }],
            knowledgeBaseTotal: 140,
            pendingRegistrations: 5,
          }),
          disclosure: drawnOpen,
        }),
      ),
    );
  }

  /*
   * The same shell WITH an instance label, which is the whole of `.am-app__instance`.
   *
   * `W41-BLIND` listed that rule as one the census cannot reach, reasoning that "a static
   * render pass has no environment to read one from". The premise was wrong in the way
   * `OPERATING_CONSTRAINTS.md` §12 describes: `getInstanceLabel()` reads
   * `process.env.NEXT_PUBLIC_INSTANCE_LABEL` in the component's own body, at render time,
   * and this harness is a node process that can set one. It was a MISSING SEED rather than
   * an unreachable branch, and a census cannot tell those apart from its own side -- which
   * is why each of the eleven had to be read in the tree rather than counted.
   *
   * The variable is restored rather than left set: this module is imported once per suite
   * and another screen reading configuration would otherwise inherit it.
   */
  {
    const before = process.env.NEXT_PUBLIC_INSTANCE_LABEL;
    process.env.NEXT_PUBLIC_INSTANCE_LABEL = 'стенд-w42b';
    try {
      add(
        'AppFrame with an instance label',
        render(createElement(AppFrame, { children: 'экран', session: null })),
      );
    } finally {
      if (before === undefined) delete process.env.NEXT_PUBLIC_INSTANCE_LABEL;
      else process.env.NEXT_PUBLIC_INSTANCE_LABEL = before;
    }
  }

  /*
   * ------------------------------------------------- the pages, DERIVED from `web/src/app`
   *
   * `D-88`. This was six hand-written lines and, further down, nine more added one wave at
   * a time as somebody noticed a screen was missing. The census's reach was therefore a
   * property of whether anybody had remembered a screen, and wave 43 measured what that
   * costs: a border at **1.08:1** on an element `BlocksPage` really rendered left `R-33`'s
   * 3:1 floor GREEN, because no screen here opened that page. The one red it did produce
   * said something false — *"no screen in `screens.ts` renders an element they match"* —
   * and named a bundler hash rather than the screen.
   *
   * `derivedScreens()` reads the route tree; `screen-set.guard.test.ts` makes an address
   * with no seed red naming the address. A screen added next wave is censused whether or
   * not anybody remembers, and a screen that brings no stylesheet of its own is now visible
   * here too — which is the half of `D-88` that moved the census in neither direction.
   */
  for (const screen of derivedScreens()) {
    add(`${screen.name} cold`, withRouter(screen.make(IDENTITY_SEGMENTS)));
  }

  /*
   * Every (screen, dynamic segment) pair with that one segment malformed, also derived.
   *
   * `.am-state--warning` and its title are the `UnsupportedState` tone — the one that says
   * no retry will help — and before wave 42 no screen in this census reached it at all.
   * Two hand-written entries reached it afterwards; eleven reach it now, and the eleven
   * come from the directory layout rather than from anybody's memory.
   */
  for (const variant of malformedVariants(IDENTITIES)) {
    add(variant.name, withRouter(variant.make()));
  }

  // A page whose query has failed: `.am-state--error` and everything inside it.
  {
    const client = newClient();
    seedError(client, queryKeys.runs.detail(RUN_ID), apiError(503, 'dependency_unavailable', true));
    add(
      'RunPage failed query',
      renderWith(client, createElement(RunProgress, { projectUid: PROJECT_UID, runId: RUN_ID })),
    );
  }

  // ------------------------------------------------------- the run, in every outcome
  add('RunProgress published', runScreen('published'));
  /*
   * A PARTIAL run, and it is a repair rather than an addition.
   *
   * This line read `runScreen('published', { stages: runStatus().stages })` -- named
   * `partial` and seeded `published`. So `.am-badge--degraded` and the run outcome
   * module's `[data-run-outcome='partial']` rule were reached by no screen in a census
   * whose own list said it covered them. `W41-BLIND` found it by asking which
   * colour-bearing rules no screen reaches, not by reading the list.
   */
  add(
    'RunProgress partial',
    runScreen('partial', { degradation_set: ['text_analysis'], published_finding_count: 1 }),
  );
  add('RunProgress failed', runScreen('failed', { terminal_reason: 'analysis_failed' as ErrorCode }));
  // `UI-A-65`: the rail states how long each stage took, and an open run draws its live line (below).
  add(
    'RunProgress published with stage times',
    runScreen('published', {
      published_finding_count: 2,
      stages: [
        { stage_id: 'source_preparation', status: 'succeeded', error_code: null, started_at: '2026-09-10T08:00:00.000Z', finished_at: '2026-09-10T08:00:00.030Z' },
        { stage_id: 'page_geometry_extraction', status: 'succeeded', error_code: null, started_at: '2026-09-10T08:00:00.030Z', finished_at: '2026-09-10T08:00:01.400Z' },
        { stage_id: 'document_context_build', status: 'partial', error_code: 'analysis_input_budget_exceeded', started_at: '2026-09-10T08:00:01.400Z', finished_at: '2026-09-10T08:01:12.000Z' },
        { stage_id: 'text_analysis', status: 'failed', error_code: 'analysis_failed', started_at: '2026-09-10T08:01:12.000Z', finished_at: '2026-09-10T08:01:13.250Z' },
      ],
    }),
  );
  add('RunProgress validating', runScreen('validating'));
  add('RunProgress queued', runScreen('queued'));
  add('RunProgress cancelled', runScreen('cancelled'));
  add(
    'RunProgress unknown vocabulary',
    runScreen('future_state' as RunState),
  );

  // ------------------------------------------------------------------ the widgets
  add('ProjectList cold', withRouter(createElement(ProjectList, {})));
  add('DocumentList cold', withRouter(createElement(DocumentList, { projectUid: PROJECT_UID })));
  add('VersionList cold', withRouter(createElement(VersionList, { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID })));
  add('RunList cold', withRouter(createElement(RunList, { projectUid: PROJECT_UID, versionUid: VERSION_UID })));
  add('UploadPanel', renderWith(newClient(), createElement(UploadPanel, { projectUid: PROJECT_UID })));

  // `UI-A-68`, `R-150f`: the shared table in its first consumer's shape -- a caption, scoped heads, rows and the
  // current row marked -- so its colour rules are measured before any screen opens the findings table.
  add(
    'Table, the findings table shape',
    render(
      createElement(Table<{ readonly id: string; readonly text: string }>, {
        caption: 'Находки прогона',
        columns: [
          { key: 'id', header: '№', cell: (row: { readonly id: string; readonly text: string }) => row.id },
          { key: 'text', header: 'Находка', cell: (row: { readonly id: string; readonly text: string }) => row.text },
        ],
        rows: [{ id: '1', text: 'Первая находка' }, { id: '2', text: 'Вторая находка' }],
        rowKey: (row: { readonly id: string; readonly text: string }) => row.id,
        currentKey: '2',
      }),
    ),
  );

  // `UI-A-24`: the context strip on a version page offers the document's other versions once there are two,
  // and says the history is longer than the page when it is -- the `.switch` and `.more` rules of the strip.
  {
    const client = populatedClient();
    const second = { ...version(), version_uid: `${VERSION_UID.slice(0, -1)}Z` as DocumentVersion['version_uid'], version_ordinal: 2 };
    client.setQueryData(queryKeys.versions.list(DOCUMENT_UID, undefined, VERSION_PAGE_LIMIT), {
      items: [version(), second],
      page: { next_cursor: 'Y3Vyc29y' },
    });
    add(
      'DocumentContext, a version of two, with more history',
      renderScreen(client, createElement(DocumentContext, { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID, versionUid: VERSION_UID, current: 'version' })),
    );
  }
  // `UI-A-28`: «‹ Предыдущий · N из M · Следующий ›» between the documents of a section -- the strip's own rules.
  {
    const neighbour = (suffix: string) => ({ ...version(), document_uid: `${DOCUMENT_UID.slice(0, -1)}${suffix}` as DocumentVersion['document_uid'], display_title: `Документ ${suffix}` });
    add(
      'SectionNeighbours, the second of three',
      render(createElement(SectionNeighboursView, {
        projectUid: PROJECT_UID,
        section: PROJECT_SECTIONS[0] as (typeof PROJECT_SECTIONS)[number],
        place: { position: 2, total: 3, previous: neighbour('A'), next: neighbour('C') },
      })),
    );
    add(
      'SectionNeighbours, the first of three',
      render(createElement(SectionNeighboursView, {
        projectUid: PROJECT_UID,
        section: PROJECT_SECTIONS[0] as (typeof PROJECT_SECTIONS)[number],
        place: { position: 1, total: 3, previous: null, next: neighbour('B') },
      })),
    );
  }
  // `UI-A-22`: the version's tabs -- the open one, a link with the finding count, a tab that is not a link yet, and the
  // document's optimisation -- so the row's current, off and count rules are measured where they are drawn.
  {
    const base = { projectUid: PROJECT_UID, versionUid: VERSION_UID, documentUid: DOCUMENT_UID, current: 'version' as const };
    add('VersionTabs, a result run to open', render(createElement(VersionTabsView, {
      tabs: versionTabs({ ...base, runs: [runStatus({ run_id: RUN_ID, published_finding_count: 7 })] }),
    })));
    add('VersionTabs, no result run yet, on «Блоки»', render(createElement(VersionTabsView, {
      tabs: versionTabs({ ...base, current: 'blocks', runs: [] }),
    })));
  }
  add('ExecutionJournal loaded', withRouter(createElement(ExecutionJournal, {
    entries: [{
      event_id: 'evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
      run_id: RUN_ID,
      aggregate_id: RUN_ID,
      aggregate_type: 'AuditRun',
      event_type: 'audit_run.transition',
      occurred_at: '2026-10-09T10:00:00Z',
      payload: { to_state: 'queued' },
    }],
    onNext: null, onPrevious: null,
  })));
  // `UI-B-40` / `UI-B-43`: the run picker at its last step with a run in view and every list cut at its first page
  // (`populatedClient` answers each with a next cursor), a step whose list could not be read, and the controls of the
  // page in both modes -- the `.picker`, `.steps`, `.step`, `.scope`, `.controls`, `.toggle`, `.count` and `.notes` rules.
  add('RunPicker at the runs, a run in view', renderScreen(populatedClient(), createElement(RunPicker, {
    selection: { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID, versionUid: VERSION_UID },
    runId: RUN_ID, onSelection: noop, onChooseRun: noop,
  })));
  {
    const client = newClient();
    client.setQueryData(queryKeys.projects.list(undefined, PROJECT_PAGE_LIMIT), { items: [project()], page: { next_cursor: null } });
    seedError(client, queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT), apiError(503, 'dependency_unavailable', true));
    add('RunPicker, the documents could not be read', renderScreen(client, createElement(RunPicker, {
      selection: { projectUid: PROJECT_UID, documentUid: null, versionUid: null },
      runId: null, onSelection: noop, onChooseRun: noop,
    })));
  }
  add('JournalControls, auto-refresh on, rows to copy', withRouter(createElement(JournalControls, {
    entries: [{
      event_id: 'evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
      run_id: RUN_ID,
      aggregate_id: RUN_ID,
      aggregate_type: 'AuditRun',
      event_type: 'audit_run.transition',
      occurred_at: '2026-10-09T10:00:00Z',
      payload: { to_state: 'queued' },
    }],
    runId: RUN_ID, autoRefresh: true, onAutoRefresh: noop,
  })));
  add('JournalControls, auto-refresh off, nothing read yet', withRouter(createElement(JournalControls, {
    entries: undefined, runId: null, autoRefresh: false, onAutoRefresh: noop,
  })));
  add('ExecutionQueue loaded', withRouter(createElement(ExecutionQueue, {
    items: [{
      job_id: 'job_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
      run_id: RUN_ID, state: 'queued', priority: 2,
      created_at: '2026-10-09T10:00:00Z',
      available_at: '2026-10-09T10:00:00Z',
      ...QUEUE_WORK,
    }],
    roles: ['admin'], asOf: Date.parse('2026-10-09T10:05:00Z'),
    busy: false, workerOf: () => ({ kind: 'pending' as const }), onCancel: noop, onReaudit: noop,
    onPriority: noop, onNext: null, onPrevious: null,
  })));
  // `UI-B-52`: two waiting jobs, each with the drag handle, the hint that names the keys and the note under the list.
  add('ExecutionQueue, waiting jobs with a handle to move each', withRouter(createElement(ExecutionQueue, {
    items: ['A', 'B'].map((suffix, index) => ({
      job_id: `job_01J9ZQ8K7NHVXW3T2R5M6P4Q8${suffix}`,
      run_id: RUN_ID, state: 'queued', priority: 2 - index,
      created_at: '2026-10-09T10:00:00Z',
      available_at: '2026-10-09T10:00:00Z',
      ...QUEUE_WORK,
    })),
    roles: ['admin'], asOf: Date.parse('2026-10-09T10:05:00Z'),
    busy: false, workerOf: () => ({ kind: 'pending' as const }), onCancel: noop, onReaudit: noop,
    onPriority: noop, onReorder: noop, reorderNote: 'Задача перемещена на место 1: приоритет 3. Порядок определил сервер.',
    onNext: null, onPrevious: null,
  })));
  // `UI-PARITY-QUEUE-A`, the queue as a line per job: a finished job with its timing, its reason and its muted facts.
  add('ExecutionQueue finished, its timing and its reason', withRouter(createElement(ExecutionQueue, {
    items: [{
      job_id: 'job_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
      run_id: RUN_ID, state: 'failed', priority: 2,
      created_at: '2026-10-09T10:00:00Z',
      available_at: '2026-10-09T10:00:00Z',
      started_at: '2026-10-09T10:01:00Z',
      finished_at: '2026-10-09T10:09:30Z',
      error_code: 'analysis_failed',
      attempt_count: 3,
      ...QUEUE_WORK,
    }],
    roles: ['admin'], asOf: Date.parse('2026-10-09T10:15:00Z'),
    busy: false, workerOf: () => ({ kind: 'pending' as const }), onCancel: noop, onReaudit: noop,
    onPriority: noop, onNext: null, onPrevious: null,
  })));
  // `UI-B-64`: the blocks under the tiles of «Обзор» -- the servers, the nearest queued jobs, a silent server and a job that ended badly.
  {
    const at = '2026-10-09T10:05:00Z';
    const job = (id: string, state: string, extra: Record<string, unknown> = {}) => ({
      job_id: `job_01J9ZQ8K7NHVXW3T2R5M6P4Q8${id}`, run_id: RUN_ID, state, priority: 0, created_at: at, available_at: at, ...QUEUE_WORK, ...extra,
    });
    add('WorkersOverviewSections with attention', withRouter(createElement(WorkersOverviewSections, {
      workers: [
        { worker_id: 'wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8A', state: 'online', intake_enabled: true, slots: 4, version: '0.5.0',
          started_at: at, heartbeat_at: at, current_run_ids: [RUN_ID] },
        { worker_id: 'wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', state: 'stale', intake_enabled: true, slots: 2, version: '0.5.0',
          started_at: at, heartbeat_at: at, current_run_ids: [] },
      ],
      workersPartial: true,
      jobs: [job('1', 'queued', { queue_position: 1 }), job('2', 'failed', { error_code: 'analysis_failed' })],
      jobsPartial: true,
      processesHref: '?tab=processes',
    } as unknown as Parameters<typeof WorkersOverviewSections>[0])));
    add('WorkersOverviewSections with nothing to attend to', withRouter(createElement(WorkersOverviewSections, {
      workers: [], workersPartial: false, jobs: [],
    })));
  }
  // The «Обновлено» line of the queue and the journal: current, and out of date (a note on the surface tint).
  add('UpdateTime fresh', withRouter(createElement(UpdateTime, {
    dataUpdatedAt: Date.parse('2026-10-09T10:05:00Z'), failed: false, now: Date.parse('2026-10-09T10:05:04Z'),
  })));
  add('UpdateTime out of date', withRouter(createElement(UpdateTime, {
    dataUpdatedAt: Date.parse('2026-10-09T10:05:00Z'), failed: true, now: Date.parse('2026-10-09T10:05:04Z'),
  })));
  // `W54-WORKERS-WEB`: a running Job names the worker holding its run, with a link to it.
  add('ExecutionQueue running, its worker named', withRouter(createElement(ExecutionQueue, {
    items: [{
      job_id: 'job_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
      run_id: RUN_ID, state: 'running', priority: 2,
      created_at: '2026-10-09T10:00:00Z',
      available_at: '2026-10-09T10:00:00Z',
      ...QUEUE_WORK,
    }],
    roles: ['expert'], asOf: Date.parse('2026-10-09T10:05:00Z'),
    busy: false,
    workerOf: () => ({ kind: 'held' as const, workerId: 'wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8A' }),
    onCancel: noop, onReaudit: noop, onPriority: noop, onNext: null, onPrevious: null,
  })));
  // `W59-ANALYSIS-SETTINGS-01`: «Настройки анализа» — a section with no profile (АР), a draft with
  // its legacy source, an authored draft with none and a section the server left unprofiled, so
  // every row shape is censused.
  // `W60-OPT-MATCH-01`: «Спецификация и цены» — a row of each status (three badge tones), a
  // counted amount beside dashes, the totals panel on its tint, and a state that stops it.
  {
    const position = 'prp_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
    const base = {
      page_number: 14, sheet_label: '10', line_start: 3, line_end: 3, table_ordinal: 1, group: null,
      unit_text: 'шт', unit: 'шт' as const, quantity_text: '12', quantity: '12', quantity_issue: null,
      mass_text: null, note: null, basis: null, reason: null, price_position: null,
      candidate_position_ids: [position], candidate_count: 1, amount: null, excluded_reason: null,
    };
    const ready = {
      project_uid: PROJECT_UID, document_uid: DOCUMENT_UID, version_uid: VERSION_UID, version_ordinal: 1,
      page_count: 8, state: 'ready' as const, project_stage: 'R' as const, section_code: 'AR' as const,
      price_list: {
        price_list_id: 'prl_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', revision_number: 1, source_filename: 'Прайс',
        uploaded_at: '2026-10-20T08:00:00Z', default_currency: 'RUB', position_count: 3,
      },
      run_id: RUN_ID, text_layer_sha256: SHA,
      extraction: {
        algorithm: 'specification-text-v1' as const, table_count: 1, row_count: 3, skipped_count: 0,
        skipped_by_reason: {
          table_header_ambiguous: 0, text_before_first_row: 0, continuation_limit: 0, anchor_ambiguous: 0,
          position_missing: 0, name_missing: 0, column_numbering: 0, rows_over_limit: 0,
        },
        skipped: [], tables: [],
      },
      matching: {
        algorithm: 'price-match-v1' as const, counts: { matched: 1, ambiguous: 1, unmatched: 1 },
        totals: [{ currency: 'RUB', amount: '180000', row_count: 1 }],
        excluded: { no_position: 1, unit_mismatch: 0, row_unit_missing: 0, ambiguous: 1, quantity_not_numeric: 0 },
      },
      rows: {
        offset: 0, limit: 50, total: 3, next_offset: null,
        items: [
          { ...base, row_id: `sr-${'a'.repeat(32)}`, group: 'Изделия', position: '1', name: 'Металлический щит', status: 'matched' as const,
            basis: 'name' as const, amount: '180000', price_position: {
              price_list_position_id: position, row_number: 1, code: null, name: 'Металлический щит', mark: null,
              unit: 'шт', unit_price: '15000', currency: 'RUB', vendor: null,
            } },
          { ...base, row_id: `sr-${'b'.repeat(32)}`, position: '2', name: 'Пена монтажная', status: 'ambiguous' as const,
            reason: 'several_positions' as const, candidate_count: 2, excluded_reason: 'ambiguous' as const },
          { ...base, row_id: `sr-${'c'.repeat(32)}`, position: '3', name: 'Профиль', status: 'unmatched' as const,
            reason: 'no_position' as const, candidate_position_ids: [], candidate_count: 0, excluded_reason: 'no_position' as const },
        ],
      },
    };
    add('SpecificationPricesAnswer ready', render(createElement(SpecificationPricesAnswer, { answer: ready, onPage: noop })));
    add('SpecificationPricesAnswer stopped', render(createElement(SpecificationPricesAnswer, {
      answer: { ...ready, state: 'price_list_missing' as const, price_list: null, run_id: null, text_layer_sha256: null,
        extraction: null, matching: null, rows: null },
      onPage: null,
    })));
  }
  // `NORM-REFS-RUN-01`: «Нормативные ссылки» — a citation of each of the five outcomes (an ok,
  // two degraded and two inert badge tones), the pages with no text layer, the legend, a corpus
  // document whose designation is not read, and a state that stops the list.
  {
    const documentA = 'ndoc_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
    const anchor = (page: number) => ({ page_number: page, char_start: 10, char_end: 26, quote: 'СП 54.13330.2011' });
    const answer = {
      run_id: RUN_ID, version_uid: VERSION_UID, state: 'ready' as const, page_count: 8,
      norms_snapshot_id: 'ns_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', text_layer_sha256: SHA, snapshot_document_count: 674,
      counts: { in_corpus: 1, newer_edition: 1, older_edition_only: 1, not_in_corpus: 1, not_recognised: 1 },
      occurrence_count: 5, unread_pages: [2],
      items: [
        { cited: 'СП 54.13330.2022', outcome: 'in_corpus' as const, occurrence_count: 1, anchors: [anchor(3)],
          matched_norm_document_id: documentA, matched_designation: 'СП 54.13330.2022', matched_title: 'Свод правил' },
        { cited: 'СП 54.13330.2011', outcome: 'newer_edition' as const, occurrence_count: 1, anchors: [anchor(1)],
          matched_norm_document_id: documentA, matched_designation: 'СП 54.13330.2024' },
        { cited: 'ГОСТ 21.101-2021', outcome: 'older_edition_only' as const, occurrence_count: 1, anchors: [anchor(4)],
          matched_norm_document_id: documentA, matched_designation: 'ГОСТ 21.101-2020' },
        { cited: 'ГОСТ Р 99999-2020', outcome: 'not_in_corpus' as const, occurrence_count: 1, anchors: [anchor(5)] },
        { cited: 'СП 54.13330', outcome: 'not_recognised' as const, occurrence_count: 1, anchors: [anchor(6)] },
      ],
      unrecognised: [{ norm_document_id: documentA, slug: 'МДС_12-24_2006', designation: 'МДС 12-24.2006', title: 'Устройство обычных' }],
    };
    add('NormReferencesAnswer ready', render(createElement(NormReferencesAnswer, { answer })));
    add('NormReferencesAnswer stopped', render(createElement(NormReferencesAnswer, {
      answer: { run_id: RUN_ID, version_uid: VERSION_UID, state: 'text_unavailable' as const, page_count: 8 },
    })));
  }
  // `W63-SECTION-FORM7-01`: «Оптимизация разделов» — a priced project beside one with no price
  // list, rows of every status (three badge tones), a counted amount beside dashes, the totals
  // per project, an excluded version, and the bound that stops the read.
  add('SectionSpecificationAnswer ready', render(createElement(SectionSpecificationAnswer, {
    answer: sectionAnswer(), onPage: noop, onSelectProject: noop,
  })));
  add('SectionSpecificationAnswer ready, with the price match', render(createElement(SectionSpecificationAnswer, {
    answer: sectionAnswer(), onPage: noop, onSelectProject: noop, columns: 'priced',
  })));
  // `UI-B-23`: a project with no specification keeps its group, said in the red of the original's «Спецификация отсутствует».
  add('SectionSpecificationAnswer, a project without a specification', render(createElement(SectionSpecificationAnswer, {
    answer: sectionAnswer({
      projects: sectionAnswer().projects.map((item, index) => (index === 1 ? { ...item, row_count: 0 } : item)),
      rows: { ...sectionAnswer().rows!, items: sectionAnswer().rows!.items.slice(0, 4), total: 4 },
    }),
    onPage: noop, onSelectProject: noop,
  })));
  add('SectionSpecificationAnswer too large', render(createElement(SectionSpecificationAnswer, {
    answer: sectionAnswer({
      ...SECTION_NO_ROWS, state: 'section_too_large', limit_reason: 'sources',
      projects: sectionAnswer().projects.map((item) => ({
        ...item, price_state: 'not_read' as const, price_list: null, matching: null, row_count: 0,
        sources: item.sources.map((source) => ({
          ...source, state: 'not_read' as const, run_id: null, text_layer_sha256: null, row_count: null,
          table_count: null, skipped_by_reason: null,
        })),
      })),
    }),
    onPage: null, onSelectProject: noop,
  })));
  // `UI-B-27`: «Принято» — the filters with the project the address names, a page with a saving and one without,
  // the empty page, and a page that has a page before and after it.
  // The page: its tabs (the open one by `aria-selected`) and the notice for an address it could not read.
  add('SectionOptimisationPage specification tab', withRouter(createElement(SectionOptimisationPage, {
    initial: readSectionOptimisationAddress({ section: 'KJ' }),
  })));
  add('SectionOptimisationPage accepted tab, an address it could not read', withRouter(createElement(SectionOptimisationPage, {
    initial: readSectionOptimisationAddress({ section: 'ZZ', tab: 'accepted' }),
  })));
  add('SectionFilterBar', render(createElement(SectionFilterBar, {
    sectionCode: 'AR', projectUid: ACCEPTED_PROJECT_A as never,
    options: [{ projectUid: ACCEPTED_PROJECT_A as never, name: 'Школа на пятьсот мест' }], onSection: noop, onProject: noop,
  })));
  add('SectionAcceptedList ready', render(createElement(SectionAcceptedList, {
    page: acceptedPage(), hasPrevious: false, onPrevious: noop, onNext: noop,
  })));
  add('SectionAcceptedList paged', render(createElement(SectionAcceptedList, {
    page: acceptedPage({ page: { next_cursor: 'c2' }, total: 41 }), hasPrevious: true, onPrevious: noop, onNext: noop,
  })));
  add('SectionAcceptedList empty', render(createElement(SectionAcceptedList, {
    page: acceptedPage({ items: [], total: 0 }), hasPrevious: false, onPrevious: noop, onNext: noop,
  })));
  add('AnalysisProfileTable loaded', render(createElement(AnalysisProfileTable, {
    items: [
      { section_code: 'AR', section_name: 'Архитектурные решения', profile: null },
      {
        section_code: 'PS', section_name: 'Пояснительная записка',
        profile: {
          analysis_profile_id: 'ap_01M5AXG1K22R027A33VTKZ468P', prompt_bundle_id: 'pb_01M5AXG1K2JQQH7R4ACTBW8974',
          profile_version: '1.0.0', status: 'draft', prompt_bundle_sha256: SHA, content_sha256: SHA,
          source: {
            repository: 'прежняя-система', commit: 'b'.repeat(40),
            files: [{ path: 'prompts/disciplines/PS/role.md', sha256: SHA }],
          },
        },
      },
      {
        // `PB-PROFILE-01`: an authored draft profile, with no legacy source.
        section_code: 'PB', section_name: 'Пожарная безопасность',
        profile: {
          analysis_profile_id: 'ap_01M5G4NZVKNZJYH722M0SXXP3X', prompt_bundle_id: 'pb_01M5G4NZVKHM9GP4EH22JACW2X',
          profile_version: '1.0.0', status: 'draft', prompt_bundle_sha256: SHA, content_sha256: SHA, source: null,
        },
      },
    ],
  })));
  // The contract allows a section with no registered profile (`profile: null`). АР is the one in the
  // shipped registry and has wording of its own (`PROD-11-AR-V1-V2-REMOVAL-01`, rendered above); the
  // generic state is rendered for the imagined `UNPROFILED`.
  add('AnalysisProfileTable one section without a profile', render(createElement(AnalysisProfileTable, {
    items: [{ section_code: UNPROFILED, section_name: 'Генеральный план', profile: null }],
  })));
  /*
   * `AR-V3-BETA-GROUP-REVIEW-SCREEN-01`: the AR v3 group review LOADED. `/analysis-settings` is
   * derived above, but with no `group_id` in its address the panel draws only its lookup form --
   * so `.member details` (the per-scope disclosure) and `.quote` (the blockquote carrying a page
   * quotation and a norm quotation) were reached by no screen, and `names every colour-bearing
   * rule that NO rendered screen reaches` said so. The address carries the group, the shape is
   * answered here: six scopes, each in a different state (available with provisional evidence,
   * failed, verification refused, three pending), seeded as the server's answer.
   */
  {
    const client = newClient();
    client.setQueryData(queryKeys.runs.arV3GroupReview(GROUP_ID), groupReviewFixture());
    // `AR-V3-DECISIONS-01`: the available scope's published finding and an expert, so `.finding`,
    // `.findings` and `.verdicts` (the findings list and the verdict controls) are reached.
    client.setQueryData(queryKeys.runs.findings(AVAILABLE_RUN_ID), { data: runFindingsPage([v3FindingFixture()]) });
    client.setQueryData(queryKeys.account.me(), accountFixture(['expert']));
    add('ArV3BetaReview six scopes loaded', renderScreen(client, createElement(ArV3BetaReview, { groupId: GROUP_ID })));
  }
  /*
   * `AR-V3-BETA-PACK-STATUS-WEB-01`: the pack panel in each of its five states, and the
   * six-check control in its three. `/analysis-settings` is derived above, but with no pack
   * answer seeded its panel is only the loading line -- so `.panel`, `.facts` and `.attestation`
   * (the installed state alone carries the last two) were reached by no screen. The control keeps
   * its refusals in a mutation observer one pass cannot settle, so its presentational view is
   * rendered with the pending state and with one warning refusal (which carries the link) and one
   * transient failure (which carries the retry).
   */
  {
    const answered = (answer: unknown): ReturnType<typeof newClient> => {
      const client = newClient();
      client.setQueryData(queryKeys.runs.arV3PackStatus(), answer);
      return client;
    };
    const pack = createElement(ArV3BetaPack);
    add('ArV3BetaPack installed', renderScreen(answered(installedPackFixture()), pack));
    add('ArV3BetaPack not installed', renderScreen(answered(NOT_INSTALLED_PACK), pack));
    add('ArV3BetaPack contract fault', renderScreen(answered(withoutMember(installedPackFixture(), 'review')), pack));
    add('ArV3BetaPack loading', renderScreen(newClient(), pack));
    {
      const client = newClient();
      seedError(client, queryKeys.runs.arV3PackStatus(), apiError(503, 'dependency_unavailable', true));
      add('ArV3BetaPack read failed', renderScreen(client, pack));
    }
    const startView = (pending: boolean, failure: ReturnType<typeof classifyArV3GroupStartFailure> | null): string =>
      renderScreen(newClient(), createElement(StartArV3GroupView, {
        projectUid: PROJECT_UID, versionUid: VERSION_UID, pending, failure, onSend: noop,
      }));
    add('StartArV3GroupView idle', startView(false, null));
    add('StartArV3GroupView pending', startView(true, null));
    add(
      'StartArV3GroupView refused with the classification link',
      startView(false, classifyArV3GroupStartFailure(apiError(422, 'version_classification_required', false))),
    );
    add(
      'StartArV3GroupView transient failure with a retry',
      startView(false, classifyArV3GroupStartFailure(apiError(503, 'dependency_unavailable', true))),
    );
  }
  // `W60-PRICE-LIST-01`: the «Оптимизация» tab loaded (revisions, a positions page with its
  // report, the fifteen vendor lists), and every other shape its widgets have.
  {
    const client = newClient();
    seedLoadedOptimisation(client);
    const loaded = optimisationShapes().find((shape) => shape.name === 'optimisation-loaded');
    if (loaded !== undefined) add('ProjectOptimisation loaded', renderScreen(client, loaded.make()));
  }
  for (const shape of optimisationShapes()) {
    if (shape.name === 'optimisation-loaded') continue;
    const client = newClient();
    shape.seedClient?.(client);
    add(`ProjectOptimisation ${shape.name}`, renderScreen(client, shape.make()));
  }
  // `W60-OPT-PROPOSALS-01`: «Предложения» loaded (a set chooser, two passes, proposals in
  // several decision states) and every other shape its widget, features and entity have.
  {
    const client = newClient();
    seedLoadedProposals(client);
    const loaded = proposalShapes().find((shape) => shape.name === 'proposals-loaded');
    if (loaded !== undefined) add('OptimisationProposals loaded', renderScreen(client, loaded.make()));
  }
  // `R-151r`: the project's summary, linking each classified document's own «Оптимизация» tab.
  {
    const client = newClient();
    client.setQueryData(queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT), {
      items: [{ ...version(), classification: { ...CONFIRMED } }],
      page: { next_cursor: 'Y3Vyc29y' },
    });
    add('OptimisationByDocument loaded', renderScreen(client, createElement(OptimisationByDocument, { projectUid: PROJECT_UID })));
  }
  for (const shape of proposalShapes()) {
    if (shape.name === 'proposals-loaded') continue;
    const client = newClient();
    shape.seedClient?.(client);
    add(`OptimisationProposals ${shape.name}`, renderScreen(client, shape.make()));
  }
  // M-17 (`R-151t`), UI-B-63: the overview tiles of «Обзор», with servers not online and a partial registry, the
  // queue's line, and the links from the tiles to «Процессы» and «Очередь» (the rules `.link` and `.queueLine`).
  const OVERVIEW_QUEUE = [
    { state: 'queued', count: 3 }, { state: 'leased', count: 0 }, { state: 'running', count: 1 },
    { state: 'retry_wait', count: 0 }, { state: 'succeeded', count: 12 }, { state: 'failed', count: 2 },
    { state: 'cancelled', count: 0 }, { state: 'dead_letter', count: 0 },
  ] as const;
  add('WorkersOverview with the queue', render(createElement(WorkersOverviewView, {
    workers: { online: 1, total: 3, onlineSlots: 4, freeSlots: 2, partial: true },
    queue: OVERVIEW_QUEUE,
    processesHref: '?tab=processes',
  })));
  {
    const client = newClient();
    client.setQueryData(queryKeys.execution.workers(undefined, WORKER_PAGE_LIMIT), {
      items: [
        {
          worker_id: 'wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8A', state: 'online', intake_enabled: true,
          slots: 4, version: '0.5.0', started_at: '2026-10-09T10:00:00Z',
          heartbeat_at: '2026-10-09T10:05:00Z', current_run_ids: [RUN_ID, RUN_ID],
        },
        {
          worker_id: 'wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8C', state: 'offline', intake_enabled: true,
          slots: 1, version: '0.4.0', started_at: '2026-10-08T09:00:00Z',
          heartbeat_at: '2026-10-08T12:00:00Z', current_run_ids: [],
        },
      ],
      page: { next_cursor: null },
    });
    client.setQueryData(queryKeys.execution.queue(undefined, {}), {
      items: [], page: { next_cursor: null }, paused: false, overview: OVERVIEW_QUEUE,
    });
    client.setQueryData(queryKeys.account.me(), { roles: ['expert'] });
    add('WorkersPage overview tab', renderScreen(client, createElement(WorkersPage as ComponentType<{ initialTab: 'overview' }>, { initialTab: 'overview' })));
  }
  // The worker registry: one row per state, the offline one in the collapsed group, and an
  // administrator's intake switch on each.
  add('WorkerList loaded', withRouter(createElement(WorkerList, {
    items: [
      {
        worker_id: 'wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8A', state: 'online', intake_enabled: true,
        slots: 1, version: '0.5.0', started_at: '2026-10-09T10:00:00Z',
        heartbeat_at: '2026-10-09T10:05:00Z', current_run_ids: [RUN_ID],
      },
      {
        worker_id: 'wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', state: 'stale', intake_enabled: false,
        slots: 2, version: '0.5.0', started_at: '2026-10-09T09:00:00Z',
        heartbeat_at: '2026-10-09T09:58:00Z', current_run_ids: [],
      },
      {
        worker_id: 'wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8C', state: 'offline', intake_enabled: true,
        slots: 1, version: '0.4.0', started_at: '2026-10-08T09:00:00Z',
        heartbeat_at: '2026-10-08T12:00:00Z', current_run_ids: [],
      },
    ],
    roles: ['admin'], busy: false, onIntake: noop, onNext: null, onPrevious: null,
  })));

  /*
   * `EXEC-HTTP-01`: «Подключения» and «Назначения». The cards carry the badges of every probe
   * outcome, the notes of a key that must be entered again and of the recent changes, and the
   * revision form and the key form; the routes carry the blocked list and the standby.
   */
  for (const [name, roles] of [['administrator', ['admin']], ['expert', ['expert']]] as const) {
    const client = newClient();
    seedExecutors(client, EXECUTOR_CASES);
    client.setQueryData(queryKeys.account.me(), { roles: [...roles] });
    add(`ExecutorConnections ${name}`, renderScreen(client, createElement(ExecutorConnections, { roles: [...roles] })));
    add(`ExecutorRoutes ${name}`, renderScreen(client, createElement(ExecutorRoutes, { roles: [...roles] })));
  }
  {
    const client = newClient();
    seedExecutors(client, EXECUTOR_CASES);
    client.setQueryData(queryKeys.account.me(), { roles: ['admin'] });
    add('WorkersPage connections tab', renderScreen(client, createElement(WorkersPage as ComponentType<{ initialTab: 'connections' | 'routes' }>, { initialTab: 'connections' })));
    add('WorkersPage routes tab', renderScreen(client, createElement(WorkersPage as ComponentType<{ initialTab: 'connections' | 'routes' }>, { initialTab: 'routes' })));
    add('Executor key form', withRouter(createElement(SetExecutorSecretForm, {
      connectionId: EXECUTOR_READY.connection.connection_id, outcome: 'saved',
    })));
    add('Executor key form refused', withRouter(createElement(SetExecutorSecretForm, {
      connectionId: EXECUTOR_READY.connection.connection_id, outcome: 'validation',
    })));
    add('Executor revision form', withRouter(createElement(ReviseConnectionForm, {
      connection: EXECUTOR_READY.connection, revision: EXECUTOR_READY.detail.revisions[0],
      pinnedModels: EXECUTOR_PINNED, holdsKey: true, onClose: noop,
    })));
  }

  /*
   * `W55B-WEB-BLOCKS`: «Блоки» once a version is chosen, which the derived `/blocks` screen
   * cannot reach (a project, a document and a tab are three clicks). Rendered through
   * `VersionBlockViews`, the component the page renders, over a seeded block list holding
   * every kind of block -- each type, a mismatch page, a polygon, a crop, flags, a
   * description, a TEXT block with no recognised text -- so every rule of the tab and the
   * portal-block modules meets the ink and tint it really sits on, in both palettes. The open
   * and the closed tab are both in the one render. The crop's address is read from the API
   * base, set for this render only and restored, the way the instance label is above; the
   * failed crop is its own view, because only a browser's `error` event selects it.
   */
  {
    const before = process.env.NEXT_PUBLIC_API_BASE_URL;
    process.env.NEXT_PUBLIC_API_BASE_URL = '/bff/v1';
    try {
      for (const tab of ['portal', 'lines'] as const) {
        const client = newClient();
        client.setQueryData(portalBlocksQueryOptions(BLOCKS_VERSION_UID).queryKey, {
          pages: [portalPage(everyKindOfBlock(), { block_count: 129, page: { next_cursor: 'c1' } })],
          pageParams: [undefined],
        });
        client.setQueryData(queryKeys.versions.blocks(BLOCKS_VERSION_UID), {
          version_uid: BLOCKS_VERSION_UID, status: 'not_produced', produced_by_run_id: null,
          text_layer_sha256: null, block_count: 0, blocks: [],
        });
        add(
          `VersionBlockViews, «${tab === 'portal' ? 'Блоки портала' : 'Строки текста'}» open`,
          renderScreen(client, createElement(VersionBlockViews, { version: blocksVersion(true), tab, onTab: noop })),
        );
      }
    } finally {
      if (before === undefined) delete process.env.NEXT_PUBLIC_API_BASE_URL;
      else process.env.NEXT_PUBLIC_API_BASE_URL = before;
    }
    // `UI-PARITY` «Блоки»: the tiles with the run's findings read (every tone of the number, the
    // amber outline, a page with none), the selector with a page chosen and the load still partial,
    // the sentence for a run with no findings and for findings that could not be read, and the block
    // view drawn open (`staticOpen`) on each kind of block: an image with the page's findings, a text
    // with its flags, a stamp with no picture, an image whose crop was not cut. The picture's failure
    // is its own view, because only a browser's `error` event selects it.
    const blocksAddress = process.env.NEXT_PUBLIC_API_BASE_URL;
    process.env.NEXT_PUBLIC_API_BASE_URL = '/bff/v1';
    try {
      const tiles = (over: Partial<Parameters<typeof PortalBlockListView>[0]>) =>
        renderScreen(newClient(), createElement(PortalBlockListView, {
          projectUid: BLOCKS_PROJECT_UID, blockCount: 129, producedByRunId: BLOCKS_RUN_ID,
          blocks: blocksOnFivePages(), versionUid: BLOCKS_VERSION_UID, hasMore: true, loadingMore: false,
          moreFailure: null, onMore: noop,
          pageFindings: { kind: 'read', runId: BLOCKS_RUN_ID, byPage: findingsByPage(runFindings()) },
          ...over,
        }));
      add('PortalBlockListView, tiles with the run’s findings', tiles({}));
      add('PortalBlockListView, one page chosen, no run', tiles({ initialPage: 2, pageFindings: { kind: 'none' } }));
      add('PortalBlockListView, the run published no findings', tiles({ pageFindings: { kind: 'no-result', runId: BLOCKS_RUN_ID } }));
      add('PortalBlockListView, the findings could not be read', tiles({ pageFindings: { kind: 'unreadable', runId: BLOCKS_RUN_ID } }));
      // `UI-PARITY-C6`: the same list numbered by BLOCK (the server's block links), «Без сущностей» with its two lists, and the
      // block view with the block's own findings. Page 3 is unlinked: its blocks carry no number and are in neither list.
      const found = runFindings();
      const heldBy = [[blockId(1)], [blockId(1), blockId(2), blockId(4)], [blockId(4)], [], []];
      const linkIndex = findingBlockIndex({
        run_id: BLOCKS_RUN_ID, version_uid: BLOCKS_VERSION_UID, status: 'produced', unlinked_pages: [3],
        items: found.map((finding, at) => ({ finding_uid: finding.finding_uid, portal_block_ids: heldBy[at] ?? [] })),
      });
      if (linkIndex === null) throw new Error('the census links must be produced');
      const byBlock: PageFindingsReading = {
        kind: 'read', runId: BLOCKS_RUN_ID, byPage: findingsByPage(found),
        blocks: { byBlock: findingsByBlock(found, linkIndex), unlinkedPages: linkIndex.unlinkedPages },
      };
      add('PortalBlockListView, tiles numbered by block', tiles({ pageFindings: byBlock }));
      add('PortalBlockListView, «Без сущностей»', tiles({ pageFindings: byBlock, initialPage: 'empty' }));
      add('Block view open on a block with its own findings', tiles({ pageFindings: byBlock, initialOpen: 0, staticOpen: true }));
      add('Block view open on a block no finding holds', tiles({ pageFindings: byBlock, initialOpen: 8, staticOpen: true }));
      add('Block view open on «Без сущностей»', tiles({ pageFindings: byBlock, initialPage: 'empty', initialOpen: 2, staticOpen: true }));
      add('Block view open on an image of a page with findings', tiles({ initialOpen: 1, staticOpen: true }));
      add('Block view open on a text with flags', tiles({ initialOpen: 0, staticOpen: true }));
      add('Block view open on a stamp', tiles({ initialOpen: 2, staticOpen: true }));
      add('Block view open on an image whose crop was not cut', tiles({ initialPage: 3, initialOpen: 0, staticOpen: true }));
      add('Block view open on a page with no findings', tiles({ initialOpen: 8, staticOpen: true }));
      add('Block view open on the last block of a page, no run', tiles({ initialPage: 2, initialOpen: 1, staticOpen: true, pageFindings: { kind: 'none' } }));
      add('BlockImageFailure', withRouter(createElement(BlockImageFailure)));
      // The card with its own crop figure (`showCrop`, the default): the block view draws the picture in its
      // stage and so leaves the figure out, which would leave the figure's rules unreached.
      for (const block of everyKindOfBlock().slice(0, 2)) {
        add(`PortalBlockCard, ${block.block_type} with the crop figure`, withRouter(createElement(PortalBlockCard, {
          block, versionUid: BLOCKS_VERSION_UID,
        })));
      }
    } finally {
      if (blocksAddress === undefined) delete process.env.NEXT_PUBLIC_API_BASE_URL;
      else process.env.NEXT_PUBLIC_API_BASE_URL = blocksAddress;
    }
    // `W55B-FIX` (Y-2): the view takes the block's identities and the seam builds the address
    // from the configured base, set for this render only.
    const crop = process.env.NEXT_PUBLIC_API_BASE_URL;
    process.env.NEXT_PUBLIC_API_BASE_URL = '/bff/v1';
    try {
      add('CropFigureView, the image failed to load', withRouter(createElement(CropFigureView, {
        versionUid: BLOCKS_VERSION_UID, portalBlockId: everyKindOfBlock()[1]!.portal_block_id,
        widthPx: 1177, heightPx: 593, alt: 'фрагмент', failed: true, onError: noop,
      })));
    } finally {
      if (crop === undefined) delete process.env.NEXT_PUBLIC_API_BASE_URL;
      else process.env.NEXT_PUBLIC_API_BASE_URL = crop;
    }
  }

  // `W55A-WEB-NORMS`: the norms widgets with rows in them — a search hit with its matched
  // spans marked, a document's paragraphs with an unreliable one marked, an administrator's
  // snapshot list with its control, and the designation history.
  add('NormSearchResults loaded', withRouter(createElement(NormSearchResults, {
    items: NORM_HITS, onFirst: noop, onNext: noop,
  })));
  add('NormDocument with an unreliable paragraph', withRouter(createElement('div', null,
    createElement(NormDocumentFacts, { document: normDocument() }),
    createElement(NormParagraphList, {
      normDocumentId: NORM_DOCUMENT_ID, items: NORM_PARAGRAPHS, onFirst: null, onNext: noop,
    }),
  )));
  /*
   * The norm's source PDF, opened at a page. It is the one surface still drawn by the browser's own
   * reader -- an `<object>` addressed by `#page=N` -- and the rule for that element used to be
   * reached by the evidence viewer's screen, which now draws with the page viewer. Without this
   * screen `.am-evidence__object` is a colour rule no screen reaches.
   */
  add('NormPdf opened at a page', withRouter(createElement(NormPdf, {
    document: normDocument(), page: 12,
    documentUrl: 'blob:https://app.test/0f0e9d8c-7b6a-5948-3726-150413021100',
    isLoading: false, error: null,
  })));
  add('NormSnapshotList loaded, administrator', withRouter(createElement(NormSnapshotList, {
    items: NORM_SNAPSHOTS, current: { kind: 'current', snapshot: NORM_SNAPSHOTS[0]! },
    canDesignate: true, busy: false, onDesignate: noop,
  })));
  add('NormSnapshotHistory loaded', withRouter(createElement(NormSnapshotHistory, {
    items: NORM_EVENTS, onFirst: null, onNext: noop,
  })));
  // `W57B-NORMS-CATALOGUE-XLSX-01`: the catalogue table with its two rows and ruled lines.
  add('NormCatalogueTable loaded', withRouter(createElement(NormCatalogueTable, {
    items: NORM_CATALOGUE_ITEMS, total: 2, filtered: false, onFirst: null, onNext: noop,
  })));

  /*
   * Lane N1: the whole of «Нормы» and of one norm document, as the pages draw them over seeded caches: the snapshot
   * strip, the two views, the search with its results, the catalogue, and an administrator's snapshots and history.
   */
  {
    const snapshots = queryKeys.norms.snapshots(undefined, NORM_SNAPSHOT_LIMIT);
    const events = queryKeys.norms.events(undefined, NORM_EVENT_PAGE_LIMIT);
    const last = { next_cursor: null };
    const seed = (): ReturnType<typeof newClient> => {
      const client = newClient();
      client.setQueryData(snapshots, { items: NORM_SNAPSHOTS, page: last });
      client.setQueryData(events, { items: NORM_EVENTS, page: last });
      return client;
    };
    const searched = seed();
    searched.setQueryData(queryKeys.norms.search('высота помещений', undefined, NORM_SEARCH_PAGE_LIMIT), {
      items: NORM_HITS, page: { next_cursor: 'c2VhcmNoLW5leHQ' },
    });
    add('NormsPage, search results, administrator', renderScreen(searched, createElement(NormsPage, {
      roles: ['admin'], query: 'высота помещений',
    })));
    add('NormsPage, no search yet, expert', renderScreen(seed(), createElement(NormsPage, { roles: ['expert'] })));
    const catalogued = seed();
    catalogued.setQueryData(
      queryKeys.norms.catalogue(undefined, undefined, undefined, NORM_CATALOGUE_PAGE_LIMIT), NORM_CATALOGUE_PAGE,
    );
    add('NormsPage, catalogue, expert', renderScreen(catalogued, createElement(NormsPage, {
      roles: ['expert'], catalogue: { q: null, kind: null },
    })));
    const narrowed = seed();
    narrowed.setQueryData(queryKeys.norms.catalogue('нет такого', 'СП', undefined, NORM_CATALOGUE_PAGE_LIMIT), {
      ...NORM_CATALOGUE_PAGE, items: [], total: 0, page: { next_cursor: null },
    });
    add('NormsPage, catalogue narrowed to nothing', renderScreen(narrowed, createElement(NormsPage, {
      roles: ['expert'], catalogue: { q: 'нет такого', kind: 'СП' },
    })));
    const bare = newClient();
    bare.setQueryData(snapshots, { items: [], page: last });
    add('NormsPage, no current snapshot', renderScreen(bare, createElement(NormsPage, { roles: ['expert'] })));
    const opened = newClient();
    opened.setQueryData(queryKeys.norms.document(NORM_DOCUMENT_ID), normDocument());
    opened.setQueryData(queryKeys.norms.paragraphs(NORM_DOCUMENT_ID, undefined, NORM_PARAGRAPH_PAGE_LIMIT), {
      items: NORM_PARAGRAPHS, page: { next_cursor: 'cGFyYWdyYXBocy1uZXh0' }, source_attribution: 'consultant_plus',
    });
    add('NormDocumentPage, a page of paragraphs', renderScreen(opened, createElement(NormDocumentPage, {
      normDocumentId: NORM_DOCUMENT_ID, page: null,
    })));
  }

  /*
   * Lane N1: «Группы», «Правила» (both modes) and «Пресеты запуска», which no other census screen reaches: a group with its
   * members and capacity, an archived one, the table of rules, and the presets with a version, a blocker and the archive.
   */
  {
    const groups = newClient();
    seedGroups(groups, [MAIN_GROUP, ROUTED_GROUP, ARCHIVED_GROUP]);
    add('ExecutorGroups administrator', renderScreen(groups, createElement(ExecutorGroups, { roles: ['admin'] })));
    const rulesLegacy = newClient();
    seedGroups(rulesLegacy, [MAIN_GROUP, ROUTED_GROUP]);
    seedRules(rulesLegacy, 'legacy', [ruleOf('text_analysis', ROUTED_GROUP, 1)]);
    add('ExecutorRules legacy mode, administrator', renderScreen(rulesLegacy, createElement(ExecutorRules, { roles: ['admin'] })));
    const rulesOn = newClient();
    seedGroups(rulesOn, [MAIN_GROUP, ROUTED_GROUP]);
    seedRules(rulesOn, 'rules', [ruleOf('text_analysis', ROUTED_GROUP, 1), ruleOf('comparison_spec', MAIN_GROUP, 2)]);
    add('ExecutorRules rules mode, expert', renderScreen(rulesOn, createElement(ExecutorRules, { roles: ['expert'] })));

    const preset = (n: number, over: Partial<AnalysisPreset> = {}): AnalysisPreset => ({
      preset_id: `evt_01M2545JSD15ETSNNV904X${String(n).padStart(4, '0')}`,
      revision_id: `evt_01M2545JSD15ETSNNV904X${String(n + 100).padStart(4, '0')}`,
      revision_no: 1,
      name: `Быстрый черновик ${n}`,
      executor_connection_id: EXECUTOR_READY.connection.connection_id,
      state: 'active',
      created_at: '2026-10-27T10:00:00Z',
      revised_at: '2026-10-27T11:00:00Z',
      revised_by: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
      ...over,
    });
    const presets = newClient();
    seedExecutors(presets, EXECUTOR_CASES);
    presets.setQueryData(ANALYSIS_PRESETS_KEY, {
      items: [preset(1, { revision_no: 3 }), preset(2), preset(3, { state: 'archived' })],
    });
    add('AnalysisPresets administrator', renderScreen(presets, createElement(AnalysisPresets, { roles: ['admin'] })));
  }

  // The finding list, with a row SELECTED — `aria-current='true'` is the only place
  // `ink-soft` meets `accent-light`.
  add(
    'FindingList selected',
    render(
      createElement(FindingList, {
        groups: groupByCategory(FINDINGS),
        selectedFindingUid: FINDING_UID,
        onSelect: noop,
        integrityFaults: [{ findingUid: FINDINGS[1]?.finding_uid ?? '', refusal: 'отказ' }],
      }),
    ),
  );
  // `R-151h`: the knowledge base's proposal half, a decision with a comment and one without.
  add('ProposalDecisions loaded', render(createElement(ProposalDecisions, {
    records: [
      {
        proposal_decision_id: 'opd_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', optimisation_proposal_id: 'opr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
        optimisation_pass_id: 'opp_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', verdict: 'accept', comment: 'Аналог подходит по характеристикам.',
        actor_label: 'Иванова А. С.', decided_at: '2026-11-06T09:00:00Z', project_uid: PROJECT_UID, project_name: 'Мост через Неву',
        document_uid: DOCUMENT_UID, document_name: 'Архитектурные решения', version_uid: VERSION_UID, section: 'AR',
        row_text: 'Дверь металлическая ДМ-1', proposed_vendor: 'ООО «Двери»', unit: 'шт',
      },
      {
        proposal_decision_id: 'opd_01J9ZQ8K7NHVXW3T2R5M6P4Q8C', optimisation_proposal_id: 'opr_01J9ZQ8K7NHVXW3T2R5M6P4Q8C',
        optimisation_pass_id: 'opp_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', verdict: 'revise', comment: null,
        actor_label: 'Иванова А. С.', decided_at: '2026-11-06T08:00:00Z', project_uid: PROJECT_UID, project_name: 'Мост через Неву',
        document_uid: DOCUMENT_UID, document_name: 'Архитектурные решения', version_uid: VERSION_UID,
        row_text: 'Лента монтажная', proposed_vendor: 'ООО «Крепёж»', unit: 'м',
      },
    ],
  })));
  // `R-151g`: an accepted finding's execution status in its row, and the control with a refusal.
  add('FindingList with an execution status', render(createElement(FindingList, {
    groups: groupByCategory(FINDINGS.map((finding, index) => index === 0
      ? { ...finding, current_verdict: 'accepted' as const, execution_status: 'amended' as const, merged_observations: [V2_OBSERVATION, V2_SIBLING] }
      : { ...finding, current_verdict: 'rejected' as const })),
    selectedFindingUid: null,
    onSelect: noop,
  })));
  add('ExecutionStatusControl with a refusal', render(createElement(ExecutionStatusControlView, {
    status: 'taken_into_account', busy: false, error: 'Статус ставится только принятой находке.', onChange: noop,
  })));
  // `R-151d`: the decision import while sending, and its report with refused rows and a file refusal.
  add('ImportDecisions while sending', render(createElement(ImportDecisionsView, {
    pending: true, report: null, failure: null, onChoose: noop,
  })));
  add('ImportDecisions with a report and a refusal', render(createElement(ImportDecisionsView, {
    pending: false,
    report: {
      run_id: RUN_ID, recorded: 2, unchanged: 40, refused: 1,
      rows: [{ row: 7, outcome: 'refused', reason: 'unknown_finding' }],
    },
    failure: 'Это не наша выгрузка: нужен лист «Замечания» с колонкой «ID замечания». Скачайте Excel заново.',
    onChoose: noop,
  })));
  // `R-151n`: ✓/✕ in each row, with the three notes a press can leave: recorded, refused, sending.
  // `UI-A-68`: the full-width table -- verdict tints, a decided severity beside a proposal, norms, merged count -- with
  // the selected finding opened under its row.
  add(
    'FindingList, table view with an opened row',
    render(
      createElement(FindingList, {
        view: 'table',
        groups: groupByCategory([
          finding({
            finding_uid: FINDING_UID,
            category: 'internal_contradiction',
            current_verdict: 'accepted',
            decided_severity: 'critical',
            execution_status: 'amended',
            observation: V2_OBSERVATION,
            merged_observations: [V2_OBSERVATION, V2_SIBLING],
          }),
          finding({ finding_uid: `${FINDING_UID.slice(0, -1)}C`, category: 'explicit_placeholder', current_verdict: 'rejected' }),
          finding({
            finding_uid: `${FINDING_UID.slice(0, -1)}D`,
            category: 'explicit_placeholder',
            current_verdict: 'pending',
            observation: observation({ proposed_severity: 'economic', norm_citations: [] }),
          }),
        ]),
        selectedFindingUid: FINDING_UID,
        onSelect: noop,
        // `UI-A-74`: the count of the portal blocks beside the number, for the one finding the run's links name.
        blockCountOf: (findingUid: string) => (findingUid === FINDING_UID ? 3 : undefined),
        renderRowActions: (row: { readonly current_verdict: Verdict }) =>
          createElement(FindingRowActions, {
            verdict: row.current_verdict, sending: null, note: null, onAccept: noop, onReject: noop,
          }),
        renderExpansion: () => createElement('p', null, 'Открытая находка: цитата на странице и решение эксперта.'),
      }),
    ),
  );
  add(
    'FindingList with row actions, recorded and refused',
    render(
      createElement(FindingList, {
        groups: groupByCategory(FINDINGS),
        selectedFindingUid: FINDING_UID,
        onSelect: noop,
        renderRowActions: (finding: { readonly finding_uid: string; readonly current_verdict: Verdict }) =>
          createElement(FindingRowActions, {
            verdict: finding.current_verdict,
            sending: finding.finding_uid === FINDING_UID ? 'accept' : null,
            note: finding.finding_uid === FINDING_UID
              ? { tone: 'ok', text: 'Записано' }
              : { tone: 'fail', text: 'Перед принятием выберите важность. Ничего не отправлено.' },
            onAccept: noop,
            onReject: noop,
          }),
      }),
    ),
  );
  // `R-151a`: the document's lifecycle controls, archived, renaming with a refusal; and an archived document's card.
  add('DocumentLifecycle archived, renaming, refused', render(createElement(DocumentLifecycleView, {
    title: 'Архитектурные решения', archived: true, draft: '', asking: false, busy: false,
    error: 'Недостаточно прав для этого действия.',
    onEdit: noop, onDraft: noop, onSave: noop, onCancelEdit: noop, onAsk: noop, onConfirm: noop, onCancelAsk: noop,
  })));
  // `R-151e`: tags on the document page (chips with remove, the add field, a refusal) and with none.
  add('DocumentTags editable, with a refusal', render(createElement(DocumentTagsView, {
    tags: ['Корпус 1', 'Секция А'], mayEdit: true, draft: 'корпус 1', busy: false, error: 'Метка не сохранена.',
    onDraft: noop, onAdd: noop, onRemove: noop,
  })));
  add('DocumentTags read-only, none', render(createElement(DocumentTagsView, {
    tags: [], mayEdit: false, draft: '', busy: false, error: null, onDraft: noop, onAdd: noop, onRemove: noop,
  })));
  // `R-151e`: the project's tag filter, from its catalogue.
  {
    const client = newClient();
    client.setQueryData(queryKeys.projects.tags(PROJECT_UID), { items: [{ tag: 'Корпус 1', document_count: 3 }] });
    client.setQueryData(
      queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT, undefined, false, undefined, undefined, 'audit'),
      { items: [{ ...version(), tags: ['Корпус 1'] }], page: { next_cursor: null } },
    );
    add('ProjectSections with a tag filter', renderScreen(client, createElement(ProjectSections, { projectUid: PROJECT_UID })));
  }
  // `UI-PARITY-DOC-AUDIT`: the chip of each audit state on a card, a partial result's mark beside it, a never-run document
  // and a card whose item carries no audit; and the section page narrowed to the documents never run (`?filter=not_run`),
  // so the chips' tones, the page's note and its «Показать все» are reached by the census.
  {
    const runId = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
    const audited = (n: string, state: 'not_run' | 'clean' | 'awaiting_decision' | 'checked', partial = false) => ({
      ...version(),
      document_uid: `doc_01J9ZQ8K7NHVXW3T2R5M6P4Q${n}` as never,
      version_uid: `ver_01J9ZQ8K7NHVXW3T2R5M6P4Q${n}` as never,
      display_title: `Документ ${n}`,
      audit: {
        state, partial,
        ...(state === 'not_run' ? {} : { result_run_id: runId }),
        finding_count: state === 'not_run' || state === 'clean' ? 0 : 3,
        undecided_finding_count: state === 'awaiting_decision' ? 2 : 0,
      },
    });
    const cards = [
      audited('A1', 'checked'), audited('A2', 'awaiting_decision', true), audited('A3', 'clean'), audited('A4', 'not_run'),
      { ...version(), document_uid: 'doc_01J9ZQ8K7NHVXW3T2R5M6P4QA5' as never, version_uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4QA5' as never },
    ];
    add('DocumentCardGrid with the four audit states', render(createElement(DocumentCardGrid, {
      documents: cards,
      addresses: () => ({ href: '/projects', documentHref: '/projects' }),
      reviewAddress: (id) => `/projects/${PROJECT_UID}/runs/${id}/review`,
    })));
    const narrowed = newClient();
    narrowed.setQueryData(
      queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT, 'AR', false, undefined, 'not_run', 'audit'),
      { items: [audited('A4', 'not_run')], page: { next_cursor: 'Y3Vyc29y' } },
    );
    add('SectionDetailPage narrowed to the documents never run', renderScreen(narrowed, createElement(SectionDetailPage, {
      projectUid: PROJECT_UID, sectionCode: 'AR', filter: 'not_run',
    })));
  }
  // `UI-A-47`: the mark of a run in flight beside the audit chip, in each of the three states of such a run, so the pending
  // badge on a card is reached by the census (a re-run over a result, a first run, a run being validated).
  {
    const runId = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
    const running = (
      n: string,
      state: 'queued' | 'running' | 'validating',
      audit: { state: 'not_run' | 'awaiting_decision' | 'checked'; result_run_id?: string; finding_count?: number; undecided_finding_count?: number },
    ) => ({
      ...version(),
      document_uid: `doc_01J9ZQ8K7NHVXW3T2R5M6P4Q${n}` as never,
      version_uid: `ver_01J9ZQ8K7NHVXW3T2R5M6P4Q${n}` as never,
      display_title: `Документ ${n}`,
      audit: { partial: false, finding_count: 0, undecided_finding_count: 0, ...audit, active_run: { run_id: `run_01J9ZQ8K7NHVXW3T2R5M6P4Q${n}`, state } },
    });
    add('DocumentCardGrid with a run in flight', render(createElement(DocumentCardGrid, {
      documents: [
        running('B1', 'queued', { state: 'checked', result_run_id: runId, finding_count: 3 }),
        running('B2', 'running', { state: 'not_run' }),
        running('B3', 'validating', { state: 'awaiting_decision', result_run_id: runId, finding_count: 3, undecided_finding_count: 2 }),
      ],
      addresses: () => ({ href: '/projects', documentHref: '/projects' }),
      reviewAddress: (id) => `/projects/${PROJECT_UID}/runs/${id}/review`,
    })));
  }
  add('DocumentCardGrid with an archived document', render(createElement(DocumentCardGrid, {
    documents: [{ ...version(), archived_at: '2026-11-06T09:00:00Z', tags: ['Корпус 1'] }],
    addresses: () => ({ href: '/projects', documentHref: '/projects' }),
  })));
  // `R-151c`: the batch start panel -- one estimate ready and started, one ready and refused, one being sent, one
  // without an estimate; the agreement and the total.
  {
    const uid = (n: string) => `ver_01J9ZQ8K7NHVXW3T2R5M6P4Q${n}` as never;
    const entries = [
      { versionUid: uid('A1'), title: 'Пояснительная записка' },
      { versionUid: uid('A2'), title: 'Архитектурные решения' },
      { versionUid: uid('A3'), title: 'Конструкции железобетонные' },
      { versionUid: uid('A4'), title: 'Генеральный план' },
    ];
    const ready = (n: string) => ({ kind: 'ready' as const, estimate: costEstimate({ version_uid: uid(n) }) });
    add(
      'BatchStartPanel, estimates read, outcomes of each kind',
      render(createElement(BatchStartPanelView, {
        projectUid: PROJECT_UID,
        entries,
        estimates: new Map<never, BatchEstimate>([
          [uid('A1'), ready('A1')], [uid('A2'), ready('A2')], [uid('A3'), ready('A3')],
          [uid('A4'), { kind: 'failed' as const, text: 'Сервис оценки недоступен.' }],
        ]),
        outcomes: new Map<never, BatchOutcome>([
          [uid('A1'), { kind: 'started' as const, run: runStatus() }],
          [uid('A2'), { kind: 'refused' as const, text: 'Версия не классифицирована.' }],
          [uid('A3'), { kind: 'sending' as const }],
        ]),
        estimating: false,
        starting: false,
        agreed: true,
        onAgree: noop,
        onStart: noop,
        onClose: noop,
      })),
    );
  }
  add(
    'FindingList failed',
    render(
      createElement(FindingList, {
        groups: [],
        selectedFindingUid: null,
        onSelect: noop,
        error: { title: 'Не удалось получить находки', detail: 'Сервис недоступен.', correlationId: 'cid-contrast-1' },
      }),
    ),
  );

  // The evidence viewer, with a quotation whose anchor disagrees with its text.
  add(
    'EvidenceViewer inconsistent',
    render(
      createElement(EvidenceViewer, {
        observation: observation({
          evidence: [
            evidence({ evidence_ordinal: 1, page_number: 7, quote: 'согласованная цитата' }),
            evidence({ evidence_ordinal: 2, page_number: 7, quote: 'рассогласованная цитата', char_start: 10, char_end: 11 }),
          ],
        }),
        activePage: 7,
        onPageChange: noop,
        documentUrl: 'blob:https://app.test/0f0e9d8c-7b6a-5948-3726-150413021100',
      }),
    ),
  );
  /*
   * The states of the page viewer that only exist after pdf.js has drawn a page in a browser,
   * which a server render pass never reaches. `PageViewerView` is the viewer as markup (no hook,
   * no effect), so each state is rendered here with fixed props: the page ready with two framed
   * targets, one active and one quiet, and the pill with its way to the target; the same page
   * dragged and gliding; the old page dimmed while the next is read; and the two states that
   * stand in for a page. Without these the colours of the frames, the badges, the fill, the pill
   * and the focus ring are rules no screen reaches.
   */
  const viewerStage = makeStage({ width: 595, height: 842 }, { width: 900, height: 700 });
  const viewerPlaced = (id: string, badge: string, top: number, quote: string): Placement => ({
    target: { id, badge, quote },
    resolution: { status: 'found', method: 'lines', occurrences: 1 },
    groups: [{
      highlights: [{ left: 60, top, width: 300, height: 12 }, { left: 60, top: top + 14, width: 180, height: 12 }],
      hull: { left: 60, top, width: 300, height: 26 },
    }],
  });
  const viewerProps = (overrides: Partial<PageViewerViewProps> = {}): PageViewerViewProps => ({
    label: 'Страница 7 проверяемого документа',
    state: 'ready',
    documentUrl: 'blob:https://app.test/0f0e9d8c-7b6a-5948-3726-150413021100',
    pageNumber: 7,
    pageCount: 31,
    stage: viewerStage,
    view: viewerStage === null ? null : fitView(viewerStage),
    placements: [viewerPlaced('q1', '1', 200, 'первая цитата'), viewerPlaced('q2', '2', 420, 'вторая цитата')],
    activeTargetId: 'q1',
    pulse: 1,
    animate: false,
    dragging: false,
    overlay: null,
    onTargetSelect: noop,
    onZoomOut: noop, onZoomIn: noop, onFit: noop, onFocus: noop,
    ...overrides,
  });
  add('PageViewer ready, one target active', render(createElement(PageViewerView, viewerProps({
    view: viewerStage === null ? null : focusView({ left: 60, top: 200, width: 300, height: 26 }, viewerStage),
  }))));
  add('PageViewer dragged and gliding', render(createElement(PageViewerView, viewerProps({ dragging: true, animate: true }))));
  add('PageViewer next page being read', render(createElement(PageViewerView, viewerProps({ state: 'rendering' }))));
  add('PageViewer loading', render(createElement(PageViewerView, viewerProps({
    state: 'loading', stage: null, view: null, placements: [],
    overlay: createElement(LoadingState, { what: 'страницу документа' }),
  }))));
  add('PageViewer failed', render(createElement(PageViewerView, viewerProps({
    state: 'failed',
    overlay: createElement(ErrorState, {
      title: 'Страницу не удалось показать',
      detail: createElement('p', null, 'В документе нет страницы 7.'),
    }),
  }))));
  add(
    'EvidenceViewer quotations placed, repeated, not found and unread',
    render(
      createElement(
        'ul',
        { className: 'am-quotation-list' },
        createElement(QuotationCard, {
          item: evidence({ evidence_ordinal: 1, page_number: 7, quote: 'найденная по разметке цитата' }),
          badge: '1', active: true, onSelect: noop,
          placement: { status: 'found', method: 'lines', occurrences: 1 },
        }),
        createElement(QuotationCard, {
          item: evidence({ evidence_ordinal: 2, page_number: 7, quote: 'повторяющаяся цитата' }),
          badge: '2', active: false, onSelect: noop,
          placement: { status: 'found', method: 'text', occurrences: 2 },
        }),
        createElement(QuotationCard, {
          item: evidence({ evidence_ordinal: 3, page_number: 7, quote: 'отсутствующая цитата' }),
          badge: '3', active: false, onSelect: noop,
          placement: { status: 'not-found', method: null, occurrences: 0 },
        }),
        createElement(QuotationCard, {
          item: evidence({ evidence_ordinal: 4, page_number: 7, quote: 'цитата на скане' }),
          badge: '4', active: false, onSelect: noop,
          placement: { status: 'no-text-layer', method: null, occurrences: 0 },
        }),
        createElement(QuotationCard, {
          item: evidence({ evidence_ordinal: 5, page_number: 7, quote: 'ещё не прочитанная цитата' }),
          badge: '5', active: false, onSelect: noop, placement: null,
        }),
      ),
    ),
  );
  // «Во весь экран» on «Разбор», open: the bar with ‹ (› at the last finding is disabled), the page filling the
  // height, and the side column with the finding, the quotations and the basis.
  add(
    'ReviewViewerDialog open on the last finding',
    render(
      createElement(ReviewViewerDialog, {
        position: 12,
        total: 12,
        onPrevious: noop,
        onNext: undefined,
        onClose: noop,
        title: 'Не указан класс огнестойкости перекрытия',
        staticOpen: true,
        children: createElement(EvidenceViewer, {
          observation: observation({
            evidence: [evidence({ evidence_ordinal: 1, page_number: 7, quote: 'перекрытие по металлическим балкам' })],
          }),
          activePage: 7,
          onPageChange: noop,
          documentUrl: 'blob:https://app.test/0f0e9d8c-7b6a-5948-3726-150413021100',
          presentation: 'full',
          aside: createElement(ReviewViewerAside, {
            findingUid: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z',
            meta: 'Критическое · Лист 3 · стр. 7',
            text: 'Не указан класс огнестойкости перекрытия',
            recommendation: 'Указать предел огнестойкости REI 45 по СП 2.13130.',
          }),
        }),
      }),
    ),
  );
  add(
    'EvidenceViewer failed',
    render(
      createElement(EvidenceViewer, {
        observation: observation({}),
        activePage: 1,
        onPageChange: noop,
        documentUrl: null,
        error: { title: 'Документ недоступен', detail: 'Файл не получен.', correlationId: 'cid-contrast-1' },
      }),
    ),
  );

  // The decision panel: refused comment, pending intent, and a failure.
  add(
    'DecisionPanel refused',
    renderWith(newClient(), createElement(DecisionPanel, {
        currentVerdict: 'accepted',
        observationId: OBSERVATION_ID,
        onAccept: noop, onReject: noop, onComment: noop,
        /*
         * `'empty'` and not a sentence. `decision-panel.tsx` renders
         * `.am-decision__refusal` only for `refusal === 'empty'`, so this screen was
         * named `DecisionPanel refused` and rendered no refusal at all -- one more
         * fixture whose NAME said it reached a state it never reached.
         */
        refusal: 'empty',
      }),
    ),
  );
  add(
    'DecisionPanel failed',
    renderWith(newClient(), createElement(DecisionPanel, {
        currentVerdict: 'pending',
        observationId: OBSERVATION_ID,
        onAccept: noop, onReject: noop, onComment: noop,
        pendingIntent: 'accept',
        error: { title: 'Решение не записано', detail: 'Повторите попытку.', correlationId: 'cid-contrast-1' },
      }),
    ),
  );

  add(
    'DecisionHistory',
    render(
      createElement(DecisionHistory, {
        events: [
          decisionEvent({ verdict: 'accepted' }),
          decisionEvent({ verdict: 'rejected' }),
          decisionEvent({ verdict: 'needs_manual_review' }),
        ],
      }),
    ),
  );
  add('DecisionHistory empty', render(createElement(DecisionHistory, { events: [] })));
  add(
    'DecisionHistory unknown vocabulary',
    render(
      createElement(DecisionHistory, {
        events: [
          {
            ...decisionEvent(),
            event_type: 'future_event',
          } as unknown as DecisionEvent,
        ],
      }),
    ),
  );

  add(
    'StageTable unknown vocabulary',
    render(
      createElement(StageTable, {
        rows: [
          {
            stageId: 'future_stage',
            status: 'succeeded',
            errorCode: null,
            startedAt: null,
            finishedAt: null,
            expected: false,
            ordinal: null,
            dependsOn: [],
          } as unknown as StageRow,
        ],
      }),
    ),
  );

  // The export panel, having already produced a file — `.am-export__last`.
  add(
    'ExportPanel exported',
    render(
      createElement(ExportPanel, {
        runId: RUN_ID, runState: 'published', providerMode: 'live',
        onExport: noop, lastFileName: 'findings.csv',
      }),
    ),
  );
  add(
    'ExportPanel not exportable',
    render(
      createElement(ExportPanel, {
        runId: RUN_ID, runState: 'queued', providerMode: 'recorded', onExport: noop,
      }),
    ),
  );
  add(
    'ExportPanel failed',
    render(
      createElement(ExportPanel, {
        runId: RUN_ID, runState: 'published', providerMode: 'live', onExport: noop, isPending: true,
        error: { title: 'Выгрузка не удалась', detail: 'Файл не создан.', correlationId: 'cid-contrast-1' },
      }),
    ),
  );
  add(
    'ExportPanel unknown vocabulary',
    render(
      createElement(ExportPanel, {
        runId: RUN_ID,
        runState: 'future_state' as RunState,
        providerMode: 'recorded',
        onExport: noop,
      }),
    ),
  );

  // ------------------------------------------------ the lists, with something in them
  {
    const client = populatedClient();
    const at = (element: ReactElement): string =>
      renderScreen(client, element);
    add('ProjectList loaded', at(createElement(ProjectList, {})));
    add('DocumentList loaded', at(createElement(DocumentList, { projectUid: PROJECT_UID })));
    add('VersionList loaded', at(createElement(VersionList, { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID })));
    add('RunList loaded', at(createElement(RunList, { projectUid: PROJECT_UID, versionUid: VERSION_UID })));
    // `RunTable`: the dense run table in the states its cells branch on — the executor and preset lines
    // under the badge (a queued run waiting for its executor, a published run started with a preset), a
    // run with a starter's label, a failed run (no «Разобрать», no findings count), a partial run, and the
    // AR v3 beta run (published, yet no canonical review to open) — so the muted second line, the
    // «неизвестно» of an absent starter, the figures and the action links are measured where they are drawn.
    {
      const runsClient = populatedClient();
      const otherId = (digit: string): string => `${RUN_ID.slice(0, -1)}${digit}`;
      const executor = { connection_id: 'exc_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', display_name: 'Основной шлюз', pin_id: 'модель-основная' };
      runsClient.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), {
        items: [
          runStatus({
            run_id: RUN_ID,
            executor,
            preset: { preset_id: 'pst_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', revision_no: 2, name: 'Быстрый черновик' },
            started_by_label: 'Проверкина А. С.',
          }),
          runStatus({ run_id: otherId('9'), state: 'queued', terminal_at: null, executor, queue_reason: 'executor_at_capacity' }),
          runStatus({ run_id: otherId('8'), state: 'running', terminal_at: null, published_finding_count: 0 }),
          runStatus({ run_id: otherId('7'), state: 'failed', terminal_reason: 'dependency_unavailable' as ErrorCode, published_finding_count: 0 }),
          runStatus({ run_id: otherId('6'), state: 'partial', degradation_set: ['text_analysis'], started_by_label: 'Проверкина А. С.' }),
          runStatus({ run_id: otherId('5'), analysis_profile_id: AR_V3_BETA_PROFILE_ID }),
        ],
        page: { next_cursor: null },
      });
      add('RunList table states', renderScreen(runsClient, createElement(RunList, { projectUid: PROJECT_UID, versionUid: VERSION_UID })));
    }
    add('ProjectsPage loaded', at(createElement(ProjectsPage, {})));
    // `UI-A-35`, `UI-A-22`: the project's page with its figures and tabs, and the document's page with its tabs and
    // neighbours strip over the same populated client.
    add('ProjectDetailPage loaded', at(createElement(ProjectDetailPage, { projectUid: PROJECT_UID, roles: ['expert'] })));
    add('DocumentDetailPage loaded', at(createElement(DocumentDetailPage, { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID, roles: ['expert'] })));
    add('VersionDetailPage loaded', at(createElement(VersionDetailPage, { projectUid: PROJECT_UID, versionUid: VERSION_UID, roles: ['expert'] })));
    /*
     * `UI-A-27` «Просмотр PDF»: the drawer is mounted by a press, which a one-pass render cannot make, so its view is drawn open from plain
     * data -- on the first page (‹ disabled, the bytes here and «Открыть PDF ↗» offered) and on the last with the bytes not yet here
     * (› disabled, no link), the two states the bar's colours branch on.
     */
    add('VersionDetailPage PDF drawer open', withRouter(createElement(DocumentViewerView, {
      title: 'АР-1 · Версия 3', page: 1, pageCount: 5, onPage: () => undefined,
      externalHref: 'blob:http://web.test/0a1b2c3d#page=1', onClose: () => undefined,
      children: createElement(LoadingState, { what: 'PDF версии' }),
    })));
    add('VersionDetailPage PDF drawer on the last page, document not read', withRouter(createElement(DocumentViewerView, {
      title: 'АР-1 · Версия 3', page: 5, pageCount: 5, onPage: () => undefined,
      externalHref: null, onClose: () => undefined,
      children: createElement(ErrorState, { title: 'PDF не удалось открыть', detail: 'Байты документа не пришли.' }),
    })));
    /*
     * The home page at `/` (`W50-HOME-01`). The derived screens above render it COLD, where it draws only its loading states; the tiles, the
     * recent projects, the expert's own work and the administrator's pending-requests tile exist only over answered reads, which are seeded
     * as `tests/unit/screens/home.test.ts` seeds them (`home-fixtures.ts` is the one set).
     */
    add('HomePage loaded, expert', renderScreen(loadedHome(), createElement(HomePage, { displayLabel: HOME_LABEL, roles: HOME_EXPERT })));
    add('HomePage loaded, administrator with requests waiting', renderScreen(loadedHome({ pending: 3 }), createElement(HomePage, { displayLabel: HOME_LABEL, roles: HOME_ADMIN })));
    add('HomePage loaded, administrator with none waiting', renderScreen(loadedHome({ pending: 0 }), createElement(HomePage, { displayLabel: HOME_LABEL, roles: HOME_ADMIN })));
    // `UI-A-10`: «Последние проекты» over items that carry `audit_counts` (the line of badges under a project's name), a project that
    // waits for decisions, one that was checked and one with no documents, so the tile's figures are measured where they are drawn.
    add(
      'HomePage loaded, recent projects with their audit figures',
      renderScreen(
        loadedHome({
          projects: homeProjectPage(HOME_PROJECTS.slice(0, 5).map((project, index) => ({
            ...project,
            audit_counts: index === 0
              ? auditCounts(8, { not_run: 3, awaiting_decision: 2, checked: 2, clean: 1, no_expert_decision: 5 })
              : index === 1 ? auditCounts(4, { not_run: 0, checked: 4, no_expert_decision: 0 }) : auditCounts(index === 2 ? 0 : 2),
          }))),
        }),
        createElement(HomePage, { displayLabel: HOME_LABEL, roles: HOME_EXPERT }),
      ),
    );
    // `CMP-VERSION-MARK-01`: the same four screens over a version admitted for comparison only
    // (`upload_kind` `comparison_pdf`): the mark on a row and in the panel, and the run list with
    // its disabled start — over a list with a run and over an empty one — so the badge's tone, the
    // wrapped mark, the disabled button and the note beside it are measured where they are drawn.
    {
      const flagged = { ...version(), upload_kind: 'comparison_pdf' as const };
      const comparisonOnly = (): ReturnType<typeof populatedClient> => {
        const client = populatedClient();
        const onePage = { next_cursor: 'Y3Vyc29y' } as { next_cursor: string };
        client.setQueryData(queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT), { items: [flagged], page: onePage });
        client.setQueryData(queryKeys.versions.list(DOCUMENT_UID, undefined, VERSION_PAGE_LIMIT), { items: [flagged], page: onePage });
        client.setQueryData(queryKeys.versions.detail(VERSION_UID), flagged);
        return client;
      };
      const atFlagged = (element: ReactElement): string => renderScreen(comparisonOnly(), element);
      add('DocumentList comparison-only', atFlagged(createElement(DocumentList, { projectUid: PROJECT_UID })));
      add('VersionList comparison-only', atFlagged(createElement(VersionList, { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID })));
      add('RunList comparison-only', atFlagged(createElement(RunList, { projectUid: PROJECT_UID, versionUid: VERSION_UID, uploadKind: 'comparison_pdf' })));
      add(
        'RunList comparison-only empty',
        (() => {
          const client = comparisonOnly();
          client.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), { items: [], page: { next_cursor: null } });
          return renderScreen(client, createElement(RunList, { projectUid: PROJECT_UID, versionUid: VERSION_UID, uploadKind: 'comparison_pdf' }));
        })(),
      );
      add('VersionDetailPage comparison-only', atFlagged(createElement(VersionDetailPage, { projectUid: PROJECT_UID, versionUid: VERSION_UID, roles: ['expert'] })));
    }
    // `CMP-DEBT-261`: the five pickers that listed a version without the mark, over a comparison-only
    // one: the version picker and the compared pair, the stage comparison page, the two set choosers
    // (a disabled option, the badge list and the reason under the select) and the blocks document
    // picker (the mark, the disabled «Показать блоки» and the reason). The badge, the note and the
    // disabled controls are measured where these screens draw them.
    {
      const OTHER_SUFFIX = 'C';
      const flaggedOther = {
        ...version(),
        version_uid: `${VERSION_UID.slice(0, -1)}${OTHER_SUFFIX}`,
        version_ordinal: 2,
        upload_kind: 'comparison_pdf' as const,
        classification: { ...CONFIRMED, version_uid: `${VERSION_UID.slice(0, -1)}${OTHER_SUFFIX}` },
      };
      const classified = { ...version(), classification: CONFIRMED };
      const flaggedSet = {
        ...flaggedOther,
        document_uid: `${DOCUMENT_UID.slice(0, -1)}${OTHER_SUFFIX}`,
        version_ordinal: 1,
      };
      const onePage = { next_cursor: null } as { next_cursor: null };
      const pickers = (): ReturnType<typeof populatedClient> => {
        const client = populatedClient();
        client.setQueryData(queryKeys.versions.list(DOCUMENT_UID, undefined, VERSION_PAGE_LIMIT), { items: [classified, flaggedOther], page: onePage });
        client.setQueryData(queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT), { items: [classified, flaggedSet], page: onePage });
        return client;
      };
      add('VersionComparison with a comparison-only version', renderScreen(pickers(), createElement(VersionComparison, { projectUid: PROJECT_UID, versionUid: VERSION_UID })));
      add('SpecificationPricesChooser with a comparison-only set', render(createElement(SpecificationPricesChooser, { sets: [classified, flaggedSet], selected: classified.document_uid, onSelect: noop, partial: false })));
      add('ProposalSetChooser with a comparison-only set', render(createElement(ProposalSetChooser, { sets: [classified, flaggedSet], selected: classified.document_uid, onSelect: noop, partial: false })));
      add('DocumentChooser with a comparison-only document', renderScreen(pickers(), createElement(DocumentChooser, { projectUid: PROJECT_UID, onChooseVersion: noop })));
      {
        const client = pickers();
        client.setQueryData(queryKeys.versions.detail(VERSION_UID), { ...classified, upload_kind: 'comparison_pdf' as const });
        add('StageComparisonPage with a comparison-only version', renderScreen(client, createElement(StageComparisonPage, { projectUid: PROJECT_UID, versionUid: VERSION_UID })));
      }
    }
    // `W59-SECTION-UI-01`: the project structure with a classified and an unclassified
    // document, the confirmed panel with a profile-less section after a refused
    // confirmation, and the form carrying a refusal.
    add(
      'ProjectStructureView loaded',
      at(
        createElement(ProjectStructureView, {
          projectUid: PROJECT_UID,
          items: [
            {
              ...version(),
              document_uid: `${DOCUMENT_UID.slice(0, -1)}C`,
              version_uid: `${VERSION_UID.slice(0, -1)}C`,
              classification: { ...CONFIRMED, version_uid: `${VERSION_UID.slice(0, -1)}C` },
            },
            // Unclassified, so its row links to the version's stage-and-section panel.
            version(),
          ],
          hasNextPage: true,
        }),
      ),
    );
    // `UI-A-36`: the same structure with the server's figures of every section, so the «Σ Итого» card is drawn.
    add(
      'ProjectStructureView with the total',
      at(
        createElement(ProjectStructureView, {
          projectUid: PROJECT_UID,
          items: [version()],
          hasNextPage: false,
          figures: sectionFigures([
            ...PROJECT_SECTION_VALUES.map((section) => ({ section, document_count: 2, ...sectionAudit(2) })),
            { document_count: 1, ...sectionAudit(1) },
          ]),
        }),
      ),
    );
    add(
      'VersionClassificationView confirmed',
      at(
        createElement(VersionClassificationView, {
          address: { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID, versionUid: VERSION_UID },
          review: sectionReviewWithoutProfile({ classification: CONFIRMED }),
          roles: ['expert'],
          conflict: true,
          onConflict: () => undefined,
        }),
      ),
    );
    // `CLASSIFICATION-CORRECTION-01`: the corrected panel with its history and the open form.
    const CORRECTED = { ...CONFIRMED, revision: 2 };
    const HISTORY = [
      {
        revision: 1,
        project_stage: 'P' as const,
        section_code: 'AR' as const,
        actor_user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
        at: '2026-10-20T08:00:00Z',
        reason: null,
      },
      {
        revision: 2,
        project_stage: CONFIRMED.project_stage,
        section_code: CONFIRMED.section_code,
        actor_user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
        at: '2026-10-21T09:30:00Z',
        reason: 'Раздел определён по штампу листа неверно.',
      },
    ];
    for (const correcting of [false, true]) {
      add(
        `VersionClassificationView corrected${correcting ? ' correcting' : ''}`,
        at(
          createElement(VersionClassificationView, {
            address: { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID, versionUid: VERSION_UID },
            review: sectionReviewWithoutProfile({ classification: CORRECTED, revisions: HISTORY }),
            roles: ['expert'],
            conflict: false,
            onConflict: () => undefined,
            correcting,
            onCorrecting: () => undefined,
          }),
        ),
      );
    }
    add(
      'CorrectVersionClassificationFormView refused',
      at(
        createElement(CorrectVersionClassificationFormView, {
          review: sectionReview(),
          current: CORRECTED,
          stage: 'P',
          section: 'AR',
          reason: '...',
          pending: false,
          failure: { kind: 'stale', detail: 'Классификацию уже изменили.', correlationId: 'cid', retryable: false },
          onStage: () => undefined,
          onSection: () => undefined,
          onReason: () => undefined,
          onSubmit: () => undefined,
          onCancel: () => undefined,
        }),
      ),
    );
    add(
      'ClassifyVersionFormView refused',
      at(
        createElement(ClassifyVersionFormView, {
          review: sectionReviewWithoutProfile(),
          stage: 'P',
          section: UNPROFILED,
          pending: false,
          failure: { kind: 'not_permitted', detail: CLASSIFY_NOT_PERMITTED_DETAIL, correlationId: 'cid', retryable: false },
          onStage: () => undefined,
          onSection: () => undefined,
          onConfirm: () => undefined,
        }),
      ),
    );
  }

  /*
   * The review screen WITH DATA IN ITS FOUR CACHES.
   *
   * `.am-review__finding h2`, `.am-review__recommendation`, `.am-review__diagnostics` and
   * `.am-uid` were reached by no screen: the census held `ReviewPage cold`, which is a
   * spinner. Three of the four caches hold the transport envelope rather than the model,
   * which is the shape `D-57` was about and the reason seeding the wrong one renders a
   * blank screen.
   */
  {
    const client = populatedClient();
    const page = { next_cursor: null } as { next_cursor: null };
    client.setQueryData(queryKeys.runs.findings(RUN_ID), { data: { items: FINDINGS, page } });
    client.setQueryData(queryKeys.findings.detail(FINDING_UID), {
      data: findingDetail({ finding_uid: FINDING_UID, decision_event_count: 2 }),
    });
    client.setQueryData(queryKeys.findings.decisions(FINDING_UID), {
      data: { items: [decisionEvent({ verdict: 'accepted' })], page },
    });
    add(
      'ReviewPage loaded',
      renderScreen(
        client,
        createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID }),
      ),
    );
  }

  /*
   * `UI-A-74`: «Блоки страницы N» under the page on «Разбор», inline and in the full-screen view's side column. The
   * default finding cites page 7, so the version's blocks are seeded under the key the «Блоки» tab fills, with
   * another cursor page waiting (the footer that offers it), and the strip is drawn through the screen itself. The
   * side column and the block view are drawn open (`staticOpen`) over a complete list; the page past the loaded
   * blocks and the unreadable blocks are their own views. The crop's address is read from the API base, set for
   * these renders only and restored.
   */
  {
    const before = process.env.NEXT_PUBLIC_API_BASE_URL;
    process.env.NEXT_PUBLIC_API_BASE_URL = '/bff/v1';
    try {
      const onPage7 = [
        imageBlock({ portal_block_id: blockId(61), page_number: 7, page_label: 7, ordinal: 1 }),
        textBlock({ portal_block_id: blockId(62), page_number: 7, page_label: 7, ordinal: 2 }),
        stampBlock({ portal_block_id: blockId(63), page_number: 7, page_label: 7 }),
      ];
      const withBlocks = (more: boolean) => {
        const client = populatedClient();
        const page = { next_cursor: null } as { next_cursor: null };
        client.setQueryData(queryKeys.runs.findings(RUN_ID), { data: { items: FINDINGS, page } });
        client.setQueryData(queryKeys.findings.detail(FINDING_UID), {
          data: findingDetail({ finding_uid: FINDING_UID, decision_event_count: 2 }),
        });
        client.setQueryData(queryKeys.findings.decisions(FINDING_UID), {
          data: { items: [decisionEvent({ verdict: 'accepted' })], page },
        });
        client.setQueryData(portalBlocksQueryOptions(VERSION_UID).queryKey, {
          pages: [portalPage(onPage7, more ? { block_count: 300, page: { next_cursor: 'c1' } } : {})],
          pageParams: [undefined],
        });
        return client;
      };
      add(
        'ReviewPage loaded, with the cited page’s blocks',
        renderScreen(withBlocks(true), createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID })),
      );
      const strip = (page: number, over: Partial<Parameters<typeof ReviewPageBlocks>[0]> = {}) =>
        createElement(ReviewPageBlocks, { projectUid: PROJECT_UID, versionUid: VERSION_UID, page, ...over });
      add(
        'ReviewViewerDialog open with the cited page’s blocks in the side column',
        renderScreen(
          withBlocks(false),
          createElement(ReviewViewerDialog, {
            position: 1,
            total: 1,
            onClose: noop,
            title: 'Не указан класс огнестойкости перекрытия',
            staticOpen: true,
            children: createElement(ReviewViewerAside, {
              findingUid: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z',
              meta: 'Критическое · Лист 3 · стр. 7',
              text: 'Не указан класс огнестойкости перекрытия',
              recommendation: 'Указать предел огнестойкости REI 45 по СП 2.13130.',
              blocks: strip(7),
            }),
          }),
        ),
      );
      add(
        'Block view open from the strip on «Разбор»',
        renderScreen(withBlocks(false), strip(7, { initialOpen: 0, staticOpen: true })),
      );
      add(
        'PageBlocksStrip, the page lies past the loaded blocks, the next portion failed',
        renderScreen(
          newClient(),
          createElement(PageBlocksStrip, {
            reading: { kind: 'not-loaded', page: 12 }, versionUid: VERSION_UID,
            onOpen: noop, onMore: noop, loadingMore: false, moreFailed: true,
          }),
        ),
      );
      add(
        'PageBlocksStrip, the next portion on its way',
        renderScreen(
          newClient(),
          createElement(PageBlocksStrip, {
            reading: { kind: 'blocks', page: 7, blocks: onPage7, complete: false }, versionUid: VERSION_UID,
            onOpen: noop, onMore: noop, loadingMore: true, moreFailed: false,
          }),
        ),
      );
      // `UI-PARITY-C6`: the finding's own blocks, connected through the run's links and the version's blocks, with the block
      // view open over them, and the strip with a block not yet loaded and the next portion on its way.
      const withLinks = (more: boolean) => {
        const client = withBlocks(more);
        client.setQueryData(queryKeys.runs.findingBlocks(RUN_ID), {
          run_id: RUN_ID, version_uid: VERSION_UID, status: 'produced', unlinked_pages: [],
          items: [{ finding_uid: FINDING_UID, portal_block_ids: [blockId(61), blockId(62)] }],
        });
        return client;
      };
      const ownBlocks = (over: Partial<Parameters<typeof ReviewFindingBlocks>[0]> = {}) =>
        createElement(ReviewFindingBlocks, { projectUid: PROJECT_UID, versionUid: VERSION_UID, runId: RUN_ID, findingUid: FINDING_UID, ...over });
      add('ReviewFindingBlocks, the finding’s own blocks', renderScreen(withLinks(false), ownBlocks()));
      add('Block view open from «Блоки замечания» on «Разбор»', renderScreen(withLinks(false), ownBlocks({ initialOpen: 1, staticOpen: true })));
      add(
        'FindingBlocksStrip, a block not yet loaded, the next portion on its way',
        renderScreen(
          newClient(),
          createElement(FindingBlocksStrip, {
            reading: { kind: 'blocks', blocks: onPage7, missing: 2, complete: false }, versionUid: VERSION_UID,
            onOpen: noop, onMore: noop, loadingMore: true, moreFailed: false,
          }),
        ),
      );
      add(
        'PageBlocksStrip, the blocks could not be read',
        renderScreen(
          newClient(),
          createElement(PageBlocksStrip, {
            reading: { kind: 'unreadable', page: 7 }, versionUid: VERSION_UID,
            onOpen: noop, onMore: noop, loadingMore: false, moreFailed: false,
          }),
        ),
      );
    } finally {
      if (before === undefined) delete process.env.NEXT_PUBLIC_API_BASE_URL;
      else process.env.NEXT_PUBLIC_API_BASE_URL = before;
    }
  }

  /*
   * `WEB-REVIEW-FOLLOWUPS-01`, item 6: the review screen WITH A v2 FINDING.
   *
   * `REVIEW-V2-UI-01` could not add this (the file is outside its paths), so its severity
   * select, proposal line, decided-severity badges, basis block and merged observations were
   * measured only through the global rules the markup happens to meet. This screen puts them
   * in the census: the finding row with its decided severity, the evidence viewer's basis and
   * merged observations, the panel with its proposal and select, and a history whose accept
   * carries a severity.
   */
  {
    const client = populatedClient();
    const page = { next_cursor: null } as { next_cursor: null };
    const detail = findingDetail({
      finding_uid: FINDING_UID,
      observation: V2_OBSERVATION,
      current_verdict: 'accepted',
      decided_severity: 'economic',
      decision_event_count: 2,
      merged_observations: [V2_OBSERVATION, V2_SIBLING],
    });
    client.setQueryData(queryKeys.runs.findings(RUN_ID), { data: { items: [detail], page } });
    client.setQueryData(queryKeys.findings.detail(FINDING_UID), { data: detail });
    client.setQueryData(queryKeys.findings.decisions(FINDING_UID), {
      data: { items: [SEVERITY_EVENTS[1] as DecisionEvent, SEVERITY_EVENTS[5] as DecisionEvent], page },
    });
    add(
      'ReviewPage loaded, v2 finding',
      renderScreen(
        client,
        createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID }),
      ),
    );
  }

  // The decision panel on a v2 finding after an accept was refused for want of a severity.
  add(
    'DecisionPanel, v2 finding, severity refused',
    renderWith(newClient(), createElement(DecisionPanel, {
        currentVerdict: 'accepted',
        observationId: OBSERVATION_ID,
        onAccept: noop, onReject: noop, onComment: noop,
        proposedSeverity: 'critical',
        decidedSeverity: 'economic',
        severityRefusal: 'severity_required',
      }),
    ),
  );

  // The history and the knowledge base with a decided severity on each accept, in all five tones.
  add('DecisionHistory with severities', render(createElement(DecisionHistory, { events: SEVERITY_EVENTS })));
  add(
    'KnowledgeBase with severities',
    render(
      createElement(KnowledgeBase, {
        records: RECORDS.map((record, index) => {
          const severity = (['critical', 'economic', 'operational', 'recommendation'] as const)[index];
          return severity === undefined ? record : { ...record, severity };
        }),
      }),
    ),
  );

  // The evidence viewer with no quotation on the page a reader is looking at.
  add(
    /*
     * RENAMED, and the old name is the finding. It was `EvidenceViewer no quotation on
     * this page` and it renders a viewer WITH a quotation: `activePage: 7` is not a page
     * this observation cites, so the viewer falls back to page 2 and shows page 2's
     * quotation. The state the name claimed is unreachable on every input (`D-85`), the
     * branch that would have rendered it is deleted this wave, and what this screen
     * actually exercises -- the fallback -- is worth a screen under its own name.
     *
     * Third instance of the shape in this file: `DecisionPanel refused` rendered no
     * refusal until wave 41, and the finding list was censused cold while named as
     * though populated. A fixture NAME is not evidence that a state was reached.
     */
    'EvidenceViewer opened at a page the observation does not cite',
    render(
      createElement(EvidenceViewer, {
        observation: observation({ evidence: [evidence({ evidence_ordinal: 1, page_number: 2 })] }),
        activePage: 7,
        onPageChange: noop,
        documentUrl: null,
      }),
    ),
  );

  // ------------------------------------------------------- the screens the list forgot
  /*
   * `W41-BLIND`, 2026-09-23. Measured, not guessed: of the 137 colour-bearing rules in
   * this application's stylesheets, **31 were reached by no screen this census renders**
   * -- 23% of the surface the census is named after. Eight of them were the knowledge
   * base, which has been in the tree since `R-23` and in this file never.
   *
   * The cause is `D-69`'s, one wave on: the census's list of screens is a hand-written
   * literal and nothing checked it against the tree. `contrast.test.ts` even asserted a
   * list of eighteen component names -- a literal checked against a literal, which is the
   * exact shape `OPERATING_CONSTRAINTS.md` §12 is about. That assertion is now derived
   * from `web/src` instead, and these are the screens it demanded.
   */

  // The knowledge base, `R-23`: eight `.am-kb__*` colour rules reached nothing before it.
  // The PAGE is derived above; the widget is not an address and stays here.
  add('KnowledgeBase', render(createElement(KnowledgeBase, { records: RECORDS })));
  // `UI-PARITY-P0A`: the place line of a record of a classified version (the rows above carry none).
  add('KnowledgeBase with a place line', render(createElement(KnowledgeBase, { records: RECORDS.map((row) => ({ ...row, section: 'AR' as const })) })));
  // `D-317`, `UI-B-34`: «Все» -- a finding's row and a proposal's row on the same three columns, under the legend.
  add('KnowledgeBase all kinds', render(createElement(KnowledgeBase, {
    records: [],
    entries: [
      ...RECORDS.slice(0, 2).map((row) => ({ kind: 'finding' as const, occurred_at: row.recorded_at, finding: { ...row, section: 'AR' as const } })),
      {
        kind: 'proposal' as const,
        occurred_at: '2026-11-06T09:00:00Z',
        proposal: {
          proposal_decision_id: 'opd_01J9ZQ8K7NHVXW3T2R5M6P4Q8D', optimisation_proposal_id: 'opr_01J9ZQ8K7NHVXW3T2R5M6P4Q8D',
          optimisation_pass_id: 'opp_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', verdict: 'accept' as const, comment: 'Аналог подходит по характеристикам.',
          actor_label: 'Иванова А. С.', decided_at: '2026-11-06T09:00:00Z', project_uid: PROJECT_UID, project_name: 'Мост через Неву',
          document_uid: DOCUMENT_UID, document_name: 'Архитектурные решения', version_uid: VERSION_UID, section: 'AR' as const,
          row_text: 'Дверь металлическая ДМ-1', proposed_vendor: 'ООО «Двери»', unit: 'шт',
        },
      },
    ],
  })));
  // `UI-B-34`: the original's table, the page's own default view: project, section, severity, verdict, reason and date by column.
  add('KnowledgeBase table', render(createElement(KnowledgeBase, {
    view: 'table', records: RECORDS.map((row) => ({ ...row, section: 'AR' as const })),
  })));
  // The table's quiet cells: a decision with no comment, and «Все» with a proposal (no severity of its own).
  add('KnowledgeBase table without comments', render(createElement(KnowledgeBase, {
    view: 'table', records: RECORDS.map((row) => ({ ...row, comment: null })),
  })));
  add('KnowledgeBase table all kinds', render(createElement(KnowledgeBase, {
    view: 'table',
    records: [],
    entries: [
      { kind: 'finding' as const, occurred_at: RECORDS[0]!.recorded_at, finding: { ...RECORDS[0]!, section: 'AR' as const } },
      {
        kind: 'proposal' as const,
        occurred_at: '2026-11-06T09:00:00Z',
        proposal: {
          proposal_decision_id: 'opd_01J9ZQ8K7NHVXW3T2R5M6P4Q8E', optimisation_proposal_id: 'opr_01J9ZQ8K7NHVXW3T2R5M6P4Q8E',
          optimisation_pass_id: 'opp_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', verdict: 'reject' as const, comment: null,
          actor_label: 'Иванова А. С.', decided_at: '2026-11-06T09:00:00Z', project_uid: PROJECT_UID, project_name: 'Мост через Неву',
          document_uid: DOCUMENT_UID, document_name: 'Архитектурные решения', version_uid: VERSION_UID, section: 'AR' as const,
          row_text: 'Дверь металлическая ДМ-1', proposed_vendor: 'ООО «Двери»', unit: 'шт',
        },
      },
    ],
  })));
  add('KnowledgeBase empty', render(createElement(KnowledgeBase, { records: [] })));
  // `D-313`: an empty page under a category, a verdict or a project says so, with both ways out on the surface.
  add('KnowledgeBase empty under a filter', render(createElement(KnowledgeBase, {
    records: [], narrowing: { onResetFilters: noop, allProjectsHref: '/knowledge-base' },
  })));

  /*
   * «Дашборд» for one project, and for a project the server does not know (`UI-PARITY-01`,
   * «Project context»). The page is derived above and is read cold there, so the loaded dashboard
   * — the scope line the hero carries — and the unknown-project state with its way out are
   * answered here: a state selected by the address's `?project=`, which a route table cannot carry.
   */
  {
    const summary: DashboardSummary = {
      documents_by_project: [{ project_uid: PROJECT_UID, name: 'Договор поставки', document_count: 3 }],
      findings_by_verdict: [
        { verdict: 'pending', count: 1 },
        { verdict: 'accepted', count: 2 },
        { verdict: 'rejected', count: 3 },
        { verdict: 'needs_manual_review', count: 4 },
      ],
      run_activity: { by_state: RUN_STATE_VALUES.map((state) => ({ state, count: 1 })) },
      section_breakdown: [
        ...PROJECT_SECTION_VALUES.map((section) => ({ section, document_count: 1, ...sectionAudit(1) })),
        { document_count: 1, ...sectionAudit(1) },
      ],
      awaiting_decision_findings: 0,
    };
    const loaded = newClient();
    loaded.setQueryData(queryKeys.dashboard.summary(PROJECT_UID), summary);
    add('Dashboard for one project', renderWith(loaded, createElement(Dashboard, { projectUid: PROJECT_UID })));

    const unknown = newClient();
    seedError(unknown, queryKeys.dashboard.summary(PROJECT_UID), apiError(404, 'not_found', false));
    add('Dashboard for an unknown project', renderWith(unknown, createElement(Dashboard, { projectUid: PROJECT_UID })));
  }

  /*
   * The session screens' OTHER SHAPES, `R-26`. `/login` and `/account/password` are
   * addresses and are derived above; a refusal and a signed-in panel are selected by props
   * that no address carries, so they stay hand-written — which is the line this file now
   * draws everywhere: the address is derived, the shape is answered.
   */
  add('SignInPage refused', render(createElement(SignInPage, { refusal: 'credentials' })));
  add('SignInPage open', render(createElement(SignInPage, { login: 'проверяющий' })));
  // The sentence above the form when the server knows why there is no session
  // (`/login?reason=…`): a rule of its own in `sign-in-page.module.css`, so the census must reach it.
  for (const reason of ['expired', 'ended', 'invalid'] as const) {
    add(`SignInPage session ${reason}`, render(createElement(SignInPage, { reason })));
  }
  add('ChangePasswordPage', render(createElement(ChangePasswordPage, { login: 'проверяющий' })));
  add(
    'ChangePasswordPage refused',
    render(createElement(ChangePasswordPage, { login: 'проверяющий', outcome: 'credentials' })),
  );
  add(
    'ChangePasswordPage changed',
    render(createElement(ChangePasswordPage, { login: 'проверяющий', outcome: 'changed' })),
  );

  {
    const client = newClient();
    client.setQueryData(queryKeys.users.list({ includeArchived: false, limit: 50 }), {
      items: [USER_ACCOUNT], page: { next_cursor: null },
    });
    add('UserList populated', renderScreen(client, createElement(UserList)));
    // `UI-A-92`: the row open beside the list is tinted, and the card stands in its panel variant.
    add('UserList with an open row', renderScreen(client, createElement(UserList, { selectedUid: USER_ACCOUNT.user_uid, onSelect: () => undefined })));
    client.setQueryData(queryKeys.users.detail(USER_ACCOUNT.user_uid), { ...USER_ACCOUNT, is_default_credential: true });
    add('UserCard panel', renderScreen(client, createElement(UserCard, { userUid: USER_ACCOUNT.user_uid, variant: 'panel', onClose: () => undefined })));
    add('UserCard page', renderScreen(client, createElement(UserCard, { userUid: USER_ACCOUNT.user_uid })));
    add('AdminAreaTabs with waiting requests', renderScreen(client, createElement(AdminAreaTabsView, { active: 'registrations', pendingTotal: 2 })));
  }
  {
    // Contract 1.36.0 (`UI-A-94`): «Журнал входов», with a line that carries a detail and one about a deleted account.
    const client = newClient();
    client.setQueryData(queryKeys.users.authEvents({ limit: 200 }), {
      items: [
        { event_id: 'evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8A', event_type: 'sign_in_succeeded', occurred_at: '2026-11-05T09:30:15Z', subject_user_uid: USER_ACCOUNT.user_uid, subject_label: USER_ACCOUNT.display_label, actor_user_uid: null, actor_label: null, source: 'api', role: null, failures: null, default_credential: true },
        { event_id: 'evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', event_type: 'role_revoked', occurred_at: '2026-11-05T09:20:00Z', subject_user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8C', subject_label: null, actor_user_uid: USER_ACCOUNT.user_uid, actor_label: USER_ACCOUNT.display_label, source: 'api', role: 'expert', failures: null, default_credential: null },
      ],
      page: { next_cursor: 'cursor-next-1' },
    });
    add('AuthEventList populated', renderScreen(client, createElement(AuthEventList)));
  }
  add('ManageUserControls active', renderScreen(newClient(), createElement(ManageUserControls, { account: USER_ACCOUNT })));
  add('ManageUserControls archived', renderScreen(newClient(), createElement(ManageUserControls, { account: { ...USER_ACCOUNT, archived_at: '2026-10-08T00:00:00Z' } })));
  {
    const client = newClient();
    client.setQueryData(queryKeys.registrations.list({ status: 'pending', limit: 50 }), {
      items: [REGISTRATION_REQUEST], page: { next_cursor: null }, pending_total: 1,
    });
    add('RegistrationQueue pending', renderScreen(client, createElement(RegistrationQueue)));
  }

  /*
   * The stage comparison, `R-23` / `W43-COMPARE`, 2026-09-24.
   *
   * THREE entries, because its colour-bearing rules are spread across its states and this
   * census measures what a screen RENDERS rather than what a file declares. The loaded
   * pair is the one that reaches `.summary`, `.choice`, `.verdict`, `.ordinal`,
   * `.instant` and `.absent` — six rules that `names every colour-bearing rule that NO
   * rendered screen reaches` listed by name the moment the module was added and this file
   * was not. That red is the reason these three lines exist, and it is worth recording
   * that it is the ONLY way this census noticed a new screen: a screen that had reused
   * the global classes and declared no module of its own would have been invisible here.
   */
  // The cold screen and its two malformed-address shapes are derived above. What is left
  // here is the one state a derivation cannot reach: the loaded PAIR.
  {
    const client = populatedClient();
    client.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), {
      items: [
        { ...runStatus({ run_id: RUN_ID }), state: 'future_state' } as unknown as RunStatus,
        runStatus({ run_id: `${RUN_ID.slice(0, -1)}C` }),
      ],
      page: { next_cursor: null },
    });
    add(
      'StageComparisonPage unknown vocabulary',
      renderScreen(
        client,
        createElement(StageComparisonPage, { projectUid: PROJECT_UID, versionUid: VERSION_UID }),
      ),
    );
  }

  {
    const client = populatedClient();
    // A SECOND run of the same version: the screen renders its tables only for a pair,
    // and a one-run cache renders the not-applicable block instead -- which would leave
    // every rule in the comparison module reached by nothing, with this file's own list
    // saying it covered them. That is the fixture-name failure this file records three
    // instances of already.
    client.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), {
      items: [
        runStatus({
          run_id: RUN_ID,
          state: 'failed',
          terminal_reason: 'dependency_unavailable' as ErrorCode,
          terminal_detail: { dependency: 'provider' },
          published_finding_count: 0,
          diagnostic_observation_count: 2,
          model_call_count: 4,
          cost_micros: 1234,
          created_at: '2026-09-11T09:00:00.000Z',
          terminal_at: '2026-09-11T09:02:30.000Z',
          stages: [
            { stage_id: 'source_preparation', status: 'succeeded', started_at: '2026-09-11T09:00:00.000Z', finished_at: '2026-09-11T09:00:30.000Z', error_code: null },
            { stage_id: 'text_analysis', status: 'failed', started_at: '2026-09-11T09:01:00.000Z', finished_at: '2026-09-11T09:02:00.000Z', error_code: 'analysis_failed' as ErrorCode },
          ],
        }),
        runStatus({
          run_id: `${RUN_ID.slice(0, -1)}C`,
          state: 'published',
          published_finding_count: 3,
          stages: [
            { stage_id: 'source_preparation', status: 'succeeded', started_at: '2026-09-10T08:00:00.000Z', finished_at: '2026-09-10T08:00:30.000Z', error_code: null },
          ],
        }),
      ],
      page: { next_cursor: null },
    });
    add(
      'StageComparisonPage with two runs',
      renderScreen(
        client,
        createElement(StageComparisonPage, { projectUid: PROJECT_UID, versionUid: VERSION_UID }),
      ),
    );
  }

  /*
   * ------------------------------------------- the shell primitives (`W50-SHELL-UI`)
   *
   * `Disclosure`, `Menu` and `Avatar` render nowhere yet -- `W50-SHELL-FRAME` composes them --
   * so without these seeds every rule they brought would be reached by no screen, and the
   * unreached-rule case above would say so. Each is rendered in each state its rules select:
   * the disclosure closed and open (its current group, its current link, the right-aligned
   * and the inline layout), the menu closed and open with its header, and one avatar per
   * colour pair. The closed states are the client islands' own server render; the open ones
   * are the views those islands render once a reader has opened them, which a static pass
   * cannot do. They sit in the application bar where the frame will put them, so the census
   * measures them on the surface they will really meet.
   */
  {
    const inBar = (...children: ReactElement[]): string =>
      render(createElement('header', { className: 'am-app__bar' }, ...children));
    const work: DisclosureProps = {
      label: 'Работа',
      links: [
        { href: '/projects', label: 'Проекты', current: true },
        { href: '/dashboard', label: 'Дашборд' },
      ],
    };
    const system: DisclosureProps = {
      label: 'Система',
      links: [
        { href: '/logs', label: 'Журнал выполнения' },
        { href: '/workers', label: 'Исполнители' },
      ],
    };
    add('Disclosure closed', inBar(createElement(Disclosure, work)));
    add(
      'Disclosure open, the current group, aligned to the end',
      inBar(
        createElement(DisclosureView, { ...work, current: true, align: 'end', open: true, panelId: 'seed-work' }),
      ),
    );
    add(
      'Disclosure open, the stacked menu holding inline groups',
      inBar(
        createElement(DisclosureView, {
          label: 'Меню',
          open: true,
          panelId: 'seed-stacked',
          children: [
            createElement(DisclosureView, {
              ...work,
              key: 'work',
              layout: 'inline',
              current: true,
              open: true,
              panelId: 'seed-stacked-work',
            }),
            createElement(DisclosureView, {
              ...system,
              key: 'system',
              layout: 'inline',
              open: false,
              panelId: 'seed-stacked-system',
            }),
          ],
        }),
      ),
    );

    const items: MenuProps['items'] = [
      { kind: 'link', label: 'Профиль', href: '/account' },
      { kind: 'link', label: 'Сменить пароль', href: '/account/password' },
      { kind: 'submit', label: 'Выйти', action: '/bff/v1/session/end' },
    ];
    const account = (): MenuProps => ({
      label: 'Учётная запись: Петрова А. С.',
      trigger: createElement(Avatar, { initials: 'ПА', colourKey: 'petrova@example.test' }),
      header: createElement('p', null, 'Петрова А. С.'),
      items,
    });
    add('Menu closed', inBar(createElement(Menu, account())));
    add(
      'Menu open, with its header',
      inBar(
        createElement(MenuView, {
          ...account(),
          state: { open: true, active: 0 },
          triggerId: 'seed-account-trigger',
          menuId: 'seed-account-menu',
        }),
      ),
    );

    // One avatar per pair. The addresses are FOUND, by hashing invented ones until every
    // pair is worn, because the pair is a property of the address and not of anything a
    // seed could name directly.
    const byPair = new Map<number, string>();
    for (let n = 1; byPair.size < AVATAR_PALETTE_SIZE && n < 1000; n += 1) {
      const address = `seed-${n}@example.test`;
      const index = avatarColourIndex(address);
      if (!byPair.has(index)) byPair.set(index, address);
    }
    add(
      'Avatar, one per colour pair',
      inBar(
        ...[...byPair]
          .sort(([a], [b]) => a - b)
          .map(([index, address]) =>
            createElement(Avatar, { key: address, initials: 'ПА', colourKey: address, label: `Пара ${index + 1}` }),
          ),
      ),
    );
  }

  // `CMP-VIEWER-01`: the sheet viewer (plan §1.1). Every rule of `comparison-viewer.module.css` is reached below: the
  // overlay with a selected difference, its boxes, the sheet being dragged and the neighbouring-sheet controls; the swipe
  // with its divider and slider; «Рядом» with the controls that are off in it; tiles that failed and tiles still on
  // their way; a pair with no evidence yet; the notes of a scan, a part of a sheet and a pair made with an AI link; and
  // the shifts and the look of lines brought into the list.
  {
    const withAlignedBlocks = comparedPair();
    add('Comparison viewer, the overlay: a selected difference, the boxes, the sheet dragged, the sheet controls',
      comparisonViewerMarkup(withAlignedBlocks, [{ type: 'boxes', on: true }, { type: 'select', index: 1 }, { type: 'align', on: true }],
        { dragging: true, navigation: true }));
    add('Comparison viewer, the swipe: divider and slider',
      comparisonViewerMarkup(comparedPair(), [{ type: 'swipe', on: true }, { type: 'swipe-position', position: 35 }, { type: 'under', under: 'b' }]));
    add('Comparison viewer, side by side: the swipe and the layers are off',
      comparisonViewerMarkup(comparedPair(), [{ type: 'mode', mode: 'side' }]));
    add('Comparison viewer, the shifts and the look of lines in the list',
      comparisonViewerMarkup(comparedPair(), [{ type: 'shifts', on: true }, { type: 'style-only', on: true }, { type: 'step', direction: 1 }]));
    add('Comparison viewer, tiles that failed',
      comparisonViewerMarkup(comparedPair(), [], { tiles: { failed: 3 } }));
    add('Comparison viewer, tiles on their way',
      comparisonViewerMarkup(comparedPair(), [], { tiles: { pending: 5, urlOf: () => null } }));
    const bare = comparedPair({ differences: [], text_changes: [], service_notes: [], reasons: [], parts: { role: 'part', covered_percent: 61.5, parts: [] },
      ai_dependent: true, page_a: { ...(comparedPair().page_a as object), scan: true } as NonNullable<ReturnType<typeof comparedPair>['page_a']> });
    delete (bare as { channels?: unknown }).channels;
    delete (bare as { how_compared?: unknown }).how_compared;
    add('Comparison viewer, a pair with no evidence yet, a scan, a part of a sheet and an AI link',
      comparisonViewerMarkup(bare, [], { tiles: { urlOf: () => null } }));
    add('Comparison viewer, a pair the viewer cannot draw', comparisonViewerMarkup(addedPair()));
    // `CMP-VC-UI-02`: the side panel «Изменения в листе» beside the sheet, and the places an AI description cites drawn on it, one at
    // a time (the current one solid) and all together («Обзор всех»).
    const cited = evidenceOf(aiDescription());
    add('Comparison viewer, every cited place at once',
      comparisonViewerMarkup(comparedPair(), [{ type: 'mode', mode: 'side' }], { evidence: { items: cited, index: 0, all: true }, sidePanel: createElement(ChangesPanelView, panelProps({ description: aiDescription({ recorded: true }), copied: true })) }));
  }

  /*
   * `CMP-VC-UI-01`: «Сравнение версий». Every state of its screens that one static pass reaches, from the one list the language
   * guard renders too (`tests/unit/version-compare/shapes.ts`): the page with its tabs, the module that is off, not wired or refused,
   * the table of document sets in every step state, the sheet matrix with its draft, its flags, its candidates, its stale and failed
   * states, the transitions in every state, the order dialog, the opened pair with the viewer, the upload dialogs with the proposal
   * and every set status, the block «Сравнение» of «Очередь» and the version-scoped screen before and after A-12. Every rule of
   * `version-series.module.css`, `comparison-upload.module.css`, `version-compare-page.module.css` and the block's part of
   * `execution-queue.module.css` is reached below.
   */
  for (const shape of COMPARISON_SHAPES) {
    const client = newClient();
    shape.seedClient?.(client);
    add(`Comparison: ${shape.name}`, renderScreen(client, shape.make()));
  }

  /*
   * `UI-PARITY-P0P`: «График работ». The month in each mode an administrator opens (the plan's inputs and settings, the
   * calendar's day and absence toggles) with a cell's «+N» list open, and «Календарь запаса» with a selection and a drop
   * target, so every rule of `work-schedule-month.module.css` and `reserve-calendar.module.css` is reached. `D-319`: the
   * month with late work in «Просрочки» (the red number), narrowed to one engineer while the count is read and failed, and
   * with an engineer the read does not carry; the reserve narrowed, and with the same unknown engineer, so the filter's
   * select and its note (`engineer-filter.module.css`) are measured.
   */
  for (const initialMode of ['view', 'plan', 'calendar'] as const) {
    add(`WorkSchedule month ${initialMode}`, renderScreen(newClient(), createElement(WorkScheduleMonthView, {
      schedule: monthFixture(), admin: true, onMonth: noop, today: '2026-11-03', initialMode,
      filter: NO_ENGINEER_FILTER, onEngineer: noop, overdue: { kind: 'ready', count: 2 },
      initialPopover: initialMode === 'view' ? `${EXPERT_A}|2026-11-03` : null,
    })));
  }
  add('WorkSchedule month narrowed to one engineer, late work still being counted', renderScreen(newClient(), createElement(WorkScheduleMonthView, {
    schedule: monthFixture(), admin: true, onMonth: noop, today: '2026-11-03', initialMode: 'view',
    filter: { uid: EXPERT_A, unknown: false }, onEngineer: noop, overdue: { kind: 'pending' },
  })));
  add('WorkSchedule month with an engineer the read does not carry, late work not loaded', renderScreen(newClient(), createElement(WorkScheduleMonthView, {
    schedule: monthFixture(), admin: true, onMonth: noop, today: '2026-11-03', initialMode: 'view',
    filter: { uid: null, unknown: true }, onEngineer: noop, overdue: { kind: 'failed' },
  })));
  add('WorkSchedule reserve', renderScreen(newClient(), createElement(ReserveCalendarView, {
    reserve: reserveFixture(), admin: true, onStart: noop, today: '2026-11-03',
    filter: NO_ENGINEER_FILTER, onEngineer: noop,
    initialSelection: [assignmentUid(1), assignmentUid(3)], initialOver: `${EXPERT_B}|2026-11-05`,
  })));
  add('WorkSchedule reserve narrowed to one engineer', renderScreen(newClient(), createElement(ReserveCalendarView, {
    reserve: reserveFixture(), admin: true, onStart: noop, today: '2026-11-03',
    filter: { uid: EXPERT_B, unknown: false }, onEngineer: noop,
  })));
  add('WorkSchedule reserve with an engineer the read does not carry', renderScreen(newClient(), createElement(ReserveCalendarView, {
    reserve: reserveFixture(), admin: true, onStart: noop, today: '2026-11-03',
    filter: { uid: null, unknown: true }, onEngineer: noop,
  })));
  // The plan met (≥ 100 %, `ok`) and half met (≥ 50 %, `warn`), and the month and the reserve with nobody in them.
  {
    const month = monthFixture();
    const [first, second] = month.engineers;
    add('WorkSchedule month, one plan met and one half met', renderScreen(newClient(), createElement(WorkScheduleMonthView, {
      schedule: {
        ...month,
        engineers: [
          ...(first === undefined ? [] : [{ ...first, plan: 5, fact: 5 }]),
          ...(second === undefined ? [] : [{ ...second, plan: 20, fact: 12 }]),
        ],
      },
      admin: false, onMonth: noop, today: '2026-11-03', initialMode: 'view', initialPopover: null,
      filter: NO_ENGINEER_FILTER, onEngineer: noop, overdue: { kind: 'ready', count: 0 },
    })));
    add('WorkSchedule month and reserve with no engineers', renderScreen(newClient(), createElement('div', null,
      createElement(WorkScheduleMonthView, {
        schedule: { ...month, engineers: [] }, admin: false, onMonth: noop, today: '2026-11-03', initialMode: 'view', initialPopover: null,
        filter: NO_ENGINEER_FILTER, onEngineer: noop, overdue: { kind: 'ready', count: 0 },
      }),
      createElement(ReserveCalendarView, {
        reserve: { ...reserveFixture(), engineers: [] }, admin: false, onStart: noop, today: '2026-11-03',
        filter: NO_ENGINEER_FILTER, onEngineer: noop,
        initialSelection: [], initialOver: null,
      }),
    )));
  }

  /*
   * A screen carrying `UnsupportedState`, which is the `warning` tone.
   *
   * `.am-state--warning` and `.am-state--warning .am-state__title` were reached by no
   * screen: every state block in this census was `neutral` or `error`, and the third tone
   * -- the one that says "no retry will help" -- was never measured in either palette. An
   * address that is not an identifier is the one way one static pass reaches it.
   */

  /*
   * `UI-B-14`: «Перенести решения из V#» in every state, and a card whose decision was carried over. They stand at the very end,
   * because the census's index test samples every 25th screen and a screen inserted earlier shifts which screens it samples.
   */
  for (const shape of carryOverShapes()) {
    const client = newClient();
    shape.seedClient?.(client);
    add(`OptimisationProposals ${shape.name}`, renderScreen(client, shape.make()));
  }
  // `UI-A-73`: «↩ Перенесено из V2» beside the verdict of a finding carried over from an earlier version, in the list and
  // in the table. Also at the very end, for the reason above.
  const carriedFrom = {
    decision_id: 'dec_01J9ZQ8K7NHVXW3T2R5M6P4Q9A', finding_uid: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q9B',
    version_uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q9C', version_ordinal: 2,
  };
  for (const view of ['list', 'table'] as const) {
    add(`FindingList ${view} with a carried verdict`, render(createElement(FindingList, {
      groups: groupByCategory(FINDINGS.map((finding, index) => index === 0
        ? { ...finding, current_verdict: 'accepted' as const, current_verdict_carried_from: carriedFrom }
        : { ...finding, current_verdict: 'rejected' as const })),
      selectedFindingUid: null,
      onSelect: noop,
      view,
    })));
  }
  // `D-344`: the knowledge base beside a decision carried over from an earlier version -- «↩ Перенесено из V2» after the event
  // label in the table (the `.carried` margin) and in the heading of an event row. The first record carries it, the rest do not,
  // so the census measures the mark on the table's cell and on a row without one. At the very end, for the reason above.
  const carriedRecords = RECORDS.map((row, index) => ({
    ...row, section: 'AR' as const, ...(index === 0 ? { carried_from: carriedFrom } : {}),
  }));
  add('KnowledgeBase table with a carried decision', render(createElement(KnowledgeBase, { view: 'table', records: carriedRecords })));
  add('KnowledgeBase with a carried decision', render(createElement(KnowledgeBase, { records: carriedRecords })));
  // `UI-B-51`, `UI-B-69`: the queue's strip of the original's three groups over the job states, one state pressed (the caption of each
  // group is the muted ink the census measures). At the very end, for the reason above.
  add('QueueStateStrip with counts', render(createElement(QueueStateStrip, {
    overview: [
      { state: 'queued', count: 3 }, { state: 'leased', count: 0 }, { state: 'running', count: 1 }, { state: 'retry_wait', count: 0 },
      { state: 'succeeded', count: 12 }, { state: 'cancelled', count: 0 }, { state: 'failed', count: 2 }, { state: 'dead_letter', count: 0 },
    ],
    selected: 'failed',
    onSelect: noop,
  })));
  /*
   * Lane N2: the screens the density pass of «Исполнители» and «Настройки анализа» measures and that no other census screen
   * draws open. The forms stand as the views the pages open them as (a closed `<details>` hides its form from a browser's layout,
   * so the group form is rendered by itself); the wizard in its steps (the kind of connection, the agent's name and model with the
   * two ways to install, the SSH form, the one command shown once, OpenRouter, and the key step after it); the runner-token
   * panel of a connection with tokens, and the box a fresh token appears in; the cut-over proposal as its table; and
   * «Настройки анализа» with the registry of every section read. At the very end, for the reason above.
   */
  {
    const wizardClient = (): ReturnType<typeof newClient> => {
      const client = newClient();
      seedExecutors(client, EXECUTOR_CASES);
      client.setQueryData(queryKeys.account.me(), { roles: ['admin'] });
      return client;
    };
    add('ConnectWizard, the kind of connection', renderScreen(wizardClient(), createElement(ConnectWizard, { pinnedModels: EXECUTOR_PINNED })));
    add('ConnectWizard, the agent: name, model and the two ways to install', renderScreen(wizardClient(), createElement(AgentSetup, {
      pinnedModels: EXECUTOR_PINNED, onBack: noop,
    })));
    add('ConnectWizard, the agent over SSH', renderScreen(wizardClient(), createElement(SshInstallForm, {
      pending: false, problem: null, failure: null, onSubmit: noop, onBack: noop,
    })));
    add('ConnectWizard, the agent: the command shown once', renderScreen(wizardClient(), createElement(EnrollmentCommandView, {
      issued: issuedEnrollment(EXECUTOR_READY.connection.connection_id), replaced: false, pending: false, failure: null,
      onNewCommand: noop, onClose: noop,
    })));
    add('ConnectWizard, OpenRouter', renderScreen(wizardClient(), createElement(OpenRouterSetup, {
      pinnedModels: EXECUTOR_PINNED, onBack: noop,
    })));
    add('ConnectWizard, OpenRouter: the key step', renderScreen(wizardClient(), createElement(OpenRouterKeyStep, {
      connectionId: EXECUTOR_READY.connection.connection_id, name: 'OpenRouter',
    })));

    const NOW_MS = Date.now();
    add('RunnerTokenPanel, a client with live, revoked and expired tokens, administrator', renderScreen(wizardClient(), createElement(RunnerTokenPanel, {
      connection: PULL_ONLINE.connection, detail: PULL_ONLINE.detail, canManage: true, nowMs: NOW_MS,
    })));
    add('RunnerTokenPanel, expert', renderScreen(wizardClient(), createElement(RunnerTokenPanel, {
      connection: PULL_ONLINE.connection, detail: PULL_ONLINE.detail, canManage: false, nowMs: NOW_MS,
    })));
    add('RunnerTokenPanel, the box of a fresh token', renderScreen(wizardClient(), createElement(IssuedTokenView, {
      issued: {
        token: 'токен-одноразовый-9f8e',
        runner_token: PULL_ONLINE.detail.runner_tokens?.[0] as NonNullable<typeof PULL_ONLINE.detail.runner_tokens>[number],
      },
      onClose: noop,
    })));

    const groupClient = (): ReturnType<typeof newClient> => {
      const client = newClient();
      seedGroups(client, [MAIN_GROUP, ROUTED_GROUP]);
      return client;
    };
    const candidates = memberCandidates(
      CONNECTION_CASES.map((one) => one.connection),
      new Map(CONNECTION_CASES.map((one) => [one.connection.connection_id, one.detail] as const)),
    );
    add('GroupForm, a new group', renderScreen(groupClient(), createElement(GroupForm, {
      candidates, pinnedModels: EXECUTOR_PINNED,
    })));
    add('GroupForm, a new revision of a group', renderScreen(groupClient(), createElement(GroupForm, {
      group: ROUTED_GROUP, candidates, pinnedModels: EXECUTOR_PINNED,
    })));
    add('CutOverPreviewTable, the proposal', renderScreen(groupClient(), createElement(CutOverPreviewTable, {
      preview: CUT_OVER_PREVIEW, connections: CONNECTION_CASES.map((one) => one.connection),
    })));

    const settings = newClient();
    settings.setQueryData(queryKeys.account.me(), { roles: ['admin'] });
    seedExecutors(settings, EXECUTOR_CASES);
    settings.setQueryData(ANALYSIS_PRESETS_KEY, { items: [] });
    settings.setQueryData(queryKeys.analysis.profiles(), {
      items: PROJECT_STRUCTURE_ORDER.map((code, index): AnalysisProfileListItem => {
        const digit = (index % 10).toString();
        return {
          section_code: code,
          section_name: projectSectionOf(code).name,
          profile: index === 3 ? null : {
            analysis_profile_id: `ap_01M5AXG1K22R027A33VTKZ468${digit}`,
            prompt_bundle_id: `pb_01M5AXG1K2JQQH7R4ACTBW897${digit}`,
            profile_version: '1.0.0',
            status: index % 2 === 0 ? 'draft' : 'reviewed',
            prompt_bundle_sha256: digit.repeat(64),
            content_sha256: 'e'.repeat(63) + digit,
            source: null,
          },
        };
      }),
    });
    add('AnalysisSettingsPage, the registry of every section read', renderScreen(settings, createElement(AnalysisSettingsPage, {})));
  }

  return out;
}
