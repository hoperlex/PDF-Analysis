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

import { AppFrame } from '@/_app';
import { DocumentDetailPage } from '@/_pages/document-detail';
import { ProjectDetailPage } from '@/_pages/project-detail';
import { ProjectsPage } from '@/_pages/projects';
import { ReviewPage } from '@/_pages/review';
import { RunPage } from '@/_pages/run';
import { VersionDetailPage } from '@/_pages/version-detail';
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
import type { ErrorCode, ErrorEnvelope, Finding, RunState, RunStatus } from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import { groupByCategory } from '@/entities/finding';

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
  add('RunProgress partial', runScreen('published', { stages: runStatus().stages }));
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
        refusal: 'Пустой комментарий не отправляется.',
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

  return out;
}
