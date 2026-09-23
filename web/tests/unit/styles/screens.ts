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
import type { ReactElement } from 'react';

import { AppRouterContext } from 'next/dist/shared/lib/app-router-context.shared-runtime';
import type { AppRouterInstance } from 'next/dist/shared/lib/app-router-context.shared-runtime';

import { DocumentDetailPage } from '@/_pages/document-detail';
import { ProjectDetailPage } from '@/_pages/project-detail';
import { ProjectsPage } from '@/_pages/projects';
import { ReviewPage } from '@/_pages/review';
import { RunPage } from '@/_pages/run';
import { VersionDetailPage } from '@/_pages/version-detail';
import { AppFrame } from '@/_app';
import { ChangePasswordPage } from '@/_pages/change-password';
import { KnowledgeBasePage } from '@/_pages/knowledge-base';
import { SignInPage } from '@/_pages/sign-in';
import { KnowledgeBase } from '@/widgets/knowledge-base';
import { DecisionHistory } from '@/widgets/decision-history';
import { DecisionPanel } from '@/widgets/decision-panel';
import { DocumentList } from '@/widgets/document-list';
import { EvidenceViewer } from '@/widgets/evidence-viewer';
import { ExportPanel } from '@/widgets/export-panel';
import { FindingList } from '@/widgets/finding-list';
import { ProjectList } from '@/widgets/project-list';
import { RunList } from '@/widgets/run-list';
import { RunProgress } from '@/widgets/run-progress';
import { UploadPanel } from '@/widgets/upload-panel';
import { VersionList } from '@/widgets/version-list';
import type { DecisionRecord, ErrorCode, ErrorEnvelope, Finding, RunState, RunStatus } from '@/shared/api';
import type { DocumentVersion, Project } from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import { groupByCategory } from '@/entities/finding';
import { PROJECT_PAGE_LIMIT } from '@/entities/project';
import { DOCUMENT_PAGE_LIMIT, VERSION_PAGE_LIMIT } from '@/entities/document-version';
import { RUN_PAGE_LIMIT } from '@/entities/audit-run';

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
import { newClient, renderWith, seedError } from '../screens/harness';

import type { Screen } from './contrast';

function stubRouter(): AppRouterInstance {
  return {
    push: () => {}, replace: () => {}, back: () => {}, forward: () => {},
    refresh: () => {}, prefetch: () => {},
  } as unknown as AppRouterInstance;
}

function withRouter(element: ReactElement): string {
  return renderWith(
    newClient(),
    createElement(AppRouterContext.Provider, { value: stubRouter() }, element),
  );
}

function apiError(status: number, code: ErrorCode, retryable: boolean): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.0.0-draft.1',
    error_code: code,
    message: 'Одна безопасная для вызывающей стороны фраза.',
    correlation_id: 'cid-contrast-1',
    retryable,
  };
  return new ApiError(status, envelope, 'cid-contrast-1');
}

const noop = (): void => {};

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
  client.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), { items: [runStatus({ run_id: RUN_ID })], page });
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
  add('AppFrame', render(createElement(AppFrame, { children: 'экран' })));

  // ------------------------------------------------------------------- the pages
  add('ProjectsPage cold', withRouter(createElement(ProjectsPage, {})));
  add('ProjectDetailPage cold', withRouter(createElement(ProjectDetailPage, { projectUid: PROJECT_UID })));
  add('VersionDetailPage cold', withRouter(createElement(VersionDetailPage, { projectUid: PROJECT_UID, versionUid: VERSION_UID })));
  add('DocumentDetailPage cold', withRouter(createElement(DocumentDetailPage, { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID })));
  add('RunPage cold', withRouter(createElement(RunPage, { projectUid: PROJECT_UID, runId: RUN_ID })));
  add('ReviewPage cold', withRouter(createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID })));

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

  // ------------------------------------------------------------------ the widgets
  add('ProjectList cold', withRouter(createElement(ProjectList, {})));
  add('DocumentList cold', withRouter(createElement(DocumentList, { projectUid: PROJECT_UID })));
  add('VersionList cold', withRouter(createElement(VersionList, { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID })));
  add('RunList cold', withRouter(createElement(RunList, { projectUid: PROJECT_UID, versionUid: VERSION_UID })));
  add('UploadPanel', renderWith(newClient(), createElement(UploadPanel, { projectUid: PROJECT_UID })));

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

  // ------------------------------------------------ the lists, with something in them
  {
    const client = populatedClient();
    const at = (element: ReactElement): string =>
      renderWith(client, createElement(AppRouterContext.Provider, { value: stubRouter() }, element));
    add('ProjectList loaded', at(createElement(ProjectList, {})));
    add('DocumentList loaded', at(createElement(DocumentList, { projectUid: PROJECT_UID })));
    add('VersionList loaded', at(createElement(VersionList, { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID })));
    add('RunList loaded', at(createElement(RunList, { projectUid: PROJECT_UID, versionUid: VERSION_UID })));
    add('ProjectsPage loaded', at(createElement(ProjectsPage, {})));
    add('VersionDetailPage loaded', at(createElement(VersionDetailPage, { projectUid: PROJECT_UID, versionUid: VERSION_UID })));
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
      renderWith(
        client,
        createElement(
          AppRouterContext.Provider,
          { value: stubRouter() },
          createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID }),
        ),
      ),
    );
  }

  // The evidence viewer with no quotation on the page a reader is looking at.
  add(
    'EvidenceViewer no quotation on this page',
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
  add('KnowledgeBasePage cold', withRouter(createElement(KnowledgeBasePage, {})));
  add('KnowledgeBase', render(createElement(KnowledgeBase, { records: RECORDS })));
  add('KnowledgeBase empty', render(createElement(KnowledgeBase, { records: [] })));

  // The session screens, `R-26`. Neither takes a query, and both carry `.am-note`.
  add('SignInPage', render(createElement(SignInPage, {})));
  add('SignInPage refused', render(createElement(SignInPage, { refusal: 'credentials' })));
  add('SignInPage open', render(createElement(SignInPage, { login: 'проверяющий' })));
  add('ChangePasswordPage signed out', render(createElement(ChangePasswordPage, {})));
  add('ChangePasswordPage', render(createElement(ChangePasswordPage, { login: 'проверяющий' })));
  add(
    'ChangePasswordPage refused',
    render(createElement(ChangePasswordPage, { login: 'проверяющий', outcome: 'credentials' })),
  );
  add(
    'ChangePasswordPage changed',
    render(createElement(ChangePasswordPage, { login: 'проверяющий', outcome: 'changed' })),
  );

  /*
   * A screen carrying `UnsupportedState`, which is the `warning` tone.
   *
   * `.am-state--warning` and `.am-state--warning .am-state__title` were reached by no
   * screen: every state block in this census was `neutral` or `error`, and the third tone
   * -- the one that says "no retry will help" -- was never measured in either palette. An
   * address that is not an identifier is the one way one static pass reaches it.
   */
  add(
    'VersionDetailPage unsupported address',
    withRouter(
      createElement(VersionDetailPage, { projectUid: PROJECT_UID, versionUid: 'not-an-identifier' }),
    ),
  );

  return out;
}
