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

import { ProjectsPage } from '@/_pages/projects';
import { ReviewPage } from '@/_pages/review';
import { VersionDetailPage } from '@/_pages/version-detail';
import { StageComparisonPage } from '@/_pages/stage-comparison';
import { AppFrame } from '@/_app';
import { accountMenuProps } from '@/_app/account-menu';
import { MarkFaultView, UpdateBannerView, WhatsNewView } from '@/_app/release-notices';
import { FrameNavigationView } from '@/_app/frame-navigation';
import { buildNavigation } from '@/_app/navigation';
import { ChangePasswordPage } from '@/_pages/change-password';
import { SignInPage } from '@/_pages/sign-in';
import { ManageUserControls } from '@/features/manage-user';
import { UserList } from '@/widgets/user-list';
import { RegistrationQueue } from '@/widgets/registration-queue';
import { VersionHistoryView } from '@/widgets/version-history';
import { KnowledgeBase } from '@/widgets/knowledge-base';
import { DecisionHistory } from '@/widgets/decision-history';
import { DecisionPanel } from '@/widgets/decision-panel';
import { DocumentList } from '@/widgets/document-list';
import { EvidenceViewer } from '@/widgets/evidence-viewer';
import { ExecutionJournal } from '@/widgets/execution-journal';
import { ExecutionQueue } from '@/widgets/execution-queue';
import { WorkerList } from '@/widgets/worker-list';
import { ExecutorConnections } from '@/widgets/executor-connections';
import { ExecutorRoutes } from '@/widgets/executor-routes';
import { WorkersPage } from '@/_pages/workers';
import { ReviseConnectionForm } from '@/features/manage-executor-connection';
import { SetExecutorSecretForm } from '@/features/set-executor-secret';
import { AnalysisProfileTable } from '@/widgets/analysis-profile-table';
import { ArV3BetaReview } from '@/widgets/ar-v3-beta-review';
import { ArV3BetaPack } from '@/widgets/ar-v3-beta-pack';
import { StartArV3GroupView, classifyArV3GroupStartFailure } from '@/features/start-ar-v3-group';
import { SpecificationPricesAnswer } from '@/widgets/specification-prices';
import { NormReferencesAnswer } from '@/widgets/norm-references';
import { SectionSpecificationAnswer } from '@/widgets/section-specification';
import { NormSearchResults } from '@/widgets/norm-search';
import { NormCatalogueTable } from '@/widgets/norm-catalogue';
import { NormDocumentFacts, NormParagraphList } from '@/widgets/norm-document';
import { NormSnapshotHistory, NormSnapshotList } from '@/widgets/norm-snapshots';
import { ExportPanel } from '@/widgets/export-panel';
import { FindingList } from '@/widgets/finding-list';
import { ProjectList } from '@/widgets/project-list';
import { RunList } from '@/widgets/run-list';
import { RunProgress } from '@/widgets/run-progress';
import { UploadPanel } from '@/widgets/upload-panel';
import { VersionList } from '@/widgets/version-list';
import { CropFigureView } from '@/widgets/portal-blocks';
import { VersionBlockViews } from '@/_pages/blocks';
import { ClassifyVersionFormView } from '@/features/classify-version';
import { CorrectVersionClassificationFormView } from '@/features/correct-version-classification';
import { ProjectStructureView } from '@/widgets/project-sections';
import { VersionClassificationView } from '@/widgets/version-classification';
import { portalBlocksQueryOptions } from '@/entities/block';
import type {
  DecisionEvent,
  DecisionRecord,
  ErrorCode,
  ErrorEnvelope,
  Finding,
  NormCitation,
  RunState,
  RunStatus,
} from '@/shared/api';
import type { DocumentVersion, Project, SectionReview } from '@/shared/api';
import type { Account } from '@/shared/api';
import type { RegistrationRequest } from '@/shared/api';
import { ApiError, PROJECT_SECTION_VALUES, queryKeys } from '@/shared/api';
import { AVATAR_PALETTE_SIZE, Avatar, Disclosure, Menu, avatarColourIndex } from '@/shared/ui';
import type { DisclosureProps, MenuProps } from '@/shared/ui';
import { DisclosureView } from '@/shared/ui/disclosure';
import { MenuView } from '@/shared/ui/menu';
import { groupByCategory } from '@/entities/finding';
import { PROJECT_PAGE_LIMIT } from '@/entities/project';
import {
  CLASSIFY_NOT_PERMITTED_DETAIL,
  DOCUMENT_PAGE_LIMIT,
  VERSION_PAGE_LIMIT,
} from '@/entities/document-version';
import type { StageRow } from '@/entities/audit-run';
import { RUN_PAGE_LIMIT, StageTable } from '@/entities/audit-run';

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
import { newClient, renderScreen, renderWith, seedError } from '../screens/harness';
import { derivedScreens, malformedVariants, wellFormed } from '../screens/route-screens';
import {
  NORM_CATALOGUE_ITEMS, NORM_DOCUMENT_ID, NORM_EVENTS, NORM_HITS, NORM_PARAGRAPHS, NORM_SNAPSHOTS,
  normDocument,
} from '../norms/fixtures';

import { BLOCKS_VERSION_UID, blocksVersion, everyKindOfBlock, portalPage } from '../blocks/fixtures';

import { optimisationShapes, seedLoadedOptimisation } from '../optimisation/fixtures';
import {
  ALL_CASES as EXECUTOR_CASES, PINNED as EXECUTOR_PINNED, READY as EXECUTOR_READY, seedExecutors,
} from '../workers/executor-fixtures';
import { proposalShapes, seedLoadedProposals } from '../optimisation-proposals/fixtures';
import { SECTION_NO_ROWS, sectionAnswer } from '../section-specification/fixtures';
import {
  AVAILABLE_RUN_ID, GROUP_ID, accountFixture, groupReviewFixture, runFindingsPage, v3FindingFixture,
} from '../analysis-settings/ar-v3-beta-review-fixtures';
import {
  NOT_INSTALLED_PACK, installedPackFixture, withoutMember,
} from '../analysis-settings/ar-v3-beta-pack-fixtures';

import type { Screen } from './contrast';

function withRouter(element: ReactElement): string {
  return renderScreen(newClient(), element);
}

function apiError(status: number, code: ErrorCode, retryable: boolean): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.9.0',
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
    for (const pathname of ['/', '/blocks']) {
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
  add('ExecutionQueue loaded', withRouter(createElement(ExecutionQueue, {
    items: [{
      job_id: 'job_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
      run_id: RUN_ID, state: 'queued', priority: 2,
      created_at: '2026-10-09T10:00:00Z',
      available_at: '2026-10-09T10:00:00Z',
    }],
    roles: ['admin'], asOf: Date.parse('2026-10-09T10:05:00Z'),
    busy: false, workerOf: () => ({ kind: 'pending' as const }), onCancel: noop, onReaudit: noop,
    onPriority: noop, onNext: null, onPrevious: null,
  })));
  // `W54-WORKERS-WEB`: a running Job names the worker holding its run, with a link to it.
  add('ExecutionQueue running, its worker named', withRouter(createElement(ExecutionQueue, {
    items: [{
      job_id: 'job_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
      run_id: RUN_ID, state: 'running', priority: 2,
      created_at: '2026-10-09T10:00:00Z',
      available_at: '2026-10-09T10:00:00Z',
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
  for (const shape of proposalShapes()) {
    if (shape.name === 'proposals-loaded') continue;
    const client = newClient();
    shape.seedClient?.(client);
    add(`OptimisationProposals ${shape.name}`, renderScreen(client, shape.make()));
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
    render(
      createElement(DecisionPanel, {
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
    render(
      createElement(DecisionPanel, {
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
    add('ProjectsPage loaded', at(createElement(ProjectsPage, {})));
    add('VersionDetailPage loaded', at(createElement(VersionDetailPage, { projectUid: PROJECT_UID, versionUid: VERSION_UID, roles: ['expert'] })));
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
    render(
      createElement(DecisionPanel, {
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
  add('KnowledgeBase empty', render(createElement(KnowledgeBase, { records: [] })));

  /*
   * The session screens' OTHER SHAPES, `R-26`. `/login` and `/account/password` are
   * addresses and are derived above; a refusal and a signed-in panel are selected by props
   * that no address carries, so they stay hand-written — which is the line this file now
   * draws everywhere: the address is derived, the shape is answered.
   */
  add('SignInPage refused', render(createElement(SignInPage, { refusal: 'credentials' })));
  add('SignInPage open', render(createElement(SignInPage, { login: 'проверяющий' })));
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

  /*
   * A screen carrying `UnsupportedState`, which is the `warning` tone.
   *
   * `.am-state--warning` and `.am-state--warning .am-state__title` were reached by no
   * screen: every state block in this census was `neutral` or `error`, and the third tone
   * -- the one that says "no retry will help" -- was never measured in either palette. An
   * address that is not an identifier is the one way one static pass reaches it.
   */
  return out;
}
