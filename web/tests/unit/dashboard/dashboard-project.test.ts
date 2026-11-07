/**
 * «Дашборд» follows the project in the address (`UI-PARITY-01`, «Project context»).
 *
 * The screen is class `optional`: without `?project=` it states «Все проекты»; with one it reads
 * `getDashboardSummary` for that project and states its name; for a project the server does not
 * know (`404 not_found`) it says «Проект не найден» with a way to «Все проекты» and never shows a
 * summary of zeros or of everything.
 *
 * Two instruments, because each sees what the other cannot. The one-pass render of `harness.ts`
 * seeds the cache under a key and reads the markup, which is how "the key carries the project" is
 * proved: seed the other key and the screen must NOT show it. The live mount presses on the real
 * route-level component with a mounted address and watches the requests, which is how "the project
 * reaches the request" and "a project change asks again" are proved.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PathnameContext, SearchParamsContext } from 'next/dist/shared/lib/hooks-client-context.shared-runtime';
import { createElement } from 'react';
import type { ReactElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, getDashboardSummary: vi.fn() };
});

import { DashboardEagerSeam, DashboardPage } from '@/_pages/dashboard';
import { ApiError, RUN_STATE_VALUES, getDashboardSummary, queryKeys } from '@/shared/api';
import type { ApiResponse, DashboardSummary, ErrorEnvelope } from '@/shared/api';
import { PROJECT_SECTIONS } from '@/entities/project';
import { Dashboard } from '@/widgets/dashboard';

import { sectionAudit } from './audit-counts';

import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { newClient, renderScreen, renderWith, seedError } from '../screens/harness';

const A = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const B = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8C';
const UNKNOWN = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8D';

/** A complete summary (every closed vocabulary whole) over the given project rows. */
function summaryOf(...projects: readonly { uid: string; name: string; documents: number }[]): DashboardSummary {
  return {
    documents_by_project: projects.map((row) => ({ project_uid: row.uid, name: row.name, document_count: row.documents })),
    findings_by_verdict: [
      { verdict: 'pending', count: 1 },
      { verdict: 'accepted', count: 2 },
      { verdict: 'rejected', count: 3 },
      { verdict: 'needs_manual_review', count: 4 },
    ],
    run_activity: { by_state: RUN_STATE_VALUES.map((state) => ({ state, count: 0 })) },
    section_breakdown: [
      ...PROJECT_SECTIONS.map((section) => ({ section: section.code, document_count: 0, ...sectionAudit(0) })),
      { document_count: 0, ...sectionAudit(0) },
    ],
    awaiting_decision_findings: 0,
  };
}

const ALL = summaryOf(
  { uid: A, name: 'Проект Альфа', documents: 3 },
  { uid: B, name: 'Проект Бета', documents: 5 },
);
const ONLY_A = summaryOf({ uid: A, name: 'Проект Альфа', documents: 3 });
const ONLY_B = summaryOf({ uid: B, name: 'Проект Бета', documents: 5 });

function notFound(): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.40.0',
    error_code: 'not_found',
    message: 'Одна безопасная для вызывающей стороны фраза.',
    correlation_id: 'cid-dashboard-404',
    retryable: false,
  };
  return new ApiError(404, envelope, 'cid-dashboard-404');
}

/** The element under the address a router would have mounted: a pathname and a query string. */
function atAddress(pathname: string, query: string, element: ReactElement): ReactElement {
  return createElement(
    PathnameContext.Provider,
    { value: pathname },
    createElement(SearchParamsContext.Provider, { value: new URLSearchParams(query) }, element),
  );
}

/** The text a browser would show: tags stripped. */
function visible(markup: string): string {
  return markup.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
}

describe('the widget states its scope', () => {
  it('says «Все проекты» when no project is asked for', () => {
    const client = newClient();
    client.setQueryData(queryKeys.dashboard.summary(), ALL);
    const markup = renderWith(client, createElement(Dashboard));
    expect(markup).toContain('data-dashboard-scope="all"');
    expect(visible(markup)).toContain('Охват Все проекты');
    // Both projects are on screen: this is the whole deployment.
    expect(markup).toContain('Проект Альфа');
    expect(markup).toContain('Проект Бета');
  });

  it('says the project’s name when one is asked for, from the same read', () => {
    const client = newClient();
    client.setQueryData(queryKeys.dashboard.summary(A), ONLY_A);
    const markup = renderWith(client, createElement(Dashboard, { projectUid: A }));
    expect(markup).toContain('data-dashboard-scope="project"');
    expect(visible(markup)).toContain('Охват Проект Альфа');
    expect(markup).not.toContain('Все проекты');
    expect(markup).not.toContain('Проект Бета');
  });

  it('names the project by the row the server sent, not by the first row', () => {
    const client = newClient();
    client.setQueryData(queryKeys.dashboard.summary(B), ALL);
    const markup = renderWith(client, createElement(Dashboard, { projectUid: B }));
    expect(visible(markup)).toContain('Охват Проект Бета');
  });

  it('shows the uid the address carries, not a made-up name, when the row is absent', () => {
    const client = newClient();
    client.setQueryData(queryKeys.dashboard.summary(UNKNOWN), summaryOf());
    const markup = renderWith(client, createElement(Dashboard, { projectUid: UNKNOWN }));
    expect(visible(markup)).toContain(`Охват ${UNKNOWN}`);
  });
});

describe('the cache key carries the project, so one project’s numbers never stand for another', () => {
  it('shows a loading state, not «Все проекты», for a project whose summary is not cached', () => {
    const client = newClient();
    client.setQueryData(queryKeys.dashboard.summary(), ALL);
    const markup = renderWith(client, createElement(Dashboard, { projectUid: A }));
    expect(markup).toContain('Загрузка: сводку по системе…');
    expect(markup).not.toContain('Проект Бета');
    expect(markup).not.toContain('data-dashboard-scope');
  });

  it('shows a loading state, not the project, for «Все проекты» when only the project is cached', () => {
    const client = newClient();
    client.setQueryData(queryKeys.dashboard.summary(A), ONLY_A);
    const markup = renderWith(client, createElement(Dashboard));
    expect(markup).toContain('Загрузка: сводку по системе…');
    expect(markup).not.toContain('data-dashboard-scope');
  });

  it('shows each project its own entry', () => {
    const client = newClient();
    client.setQueryData(queryKeys.dashboard.summary(A), ONLY_A);
    client.setQueryData(queryKeys.dashboard.summary(B), ONLY_B);
    expect(visible(renderWith(client, createElement(Dashboard, { projectUid: A })))).toContain('Охват Проект Альфа');
    expect(visible(renderWith(client, createElement(Dashboard, { projectUid: B })))).toContain('Охват Проект Бета');
  });
});

describe('an unknown project is its own state', () => {
  it('says «Проект не найден» with a link to «Все проекты», and shows no panel', () => {
    const client = newClient();
    seedError(client, queryKeys.dashboard.summary(UNKNOWN), notFound());
    const markup = renderWith(
      client,
      createElement(Dashboard, { projectUid: UNKNOWN, allProjectsHref: '/dashboard?x=1' }),
    );
    expect(markup).toContain('Проект не найден');
    expect(markup).toContain('data-dashboard-scope="unknown-project"');
    expect(markup).toMatch(/<a [^>]*href="\/dashboard\?x=1"[^>]*>Все проекты<\/a>/);
    expect(markup).toContain('cid-dashboard-404');
    // Neither a summary of zeros nor of everything.
    expect(markup).not.toContain('Охват');
    expect(markup).not.toContain('data-widget="dashboard"');
    // A project that is not there is not a failure to retry.
    expect(markup).not.toContain('Повторить');
  });

  it('can fail: the same refusal with no project asked for is the generic read failure', () => {
    const client = newClient();
    seedError(client, queryKeys.dashboard.summary(), notFound());
    const markup = renderWith(client, createElement(Dashboard));
    expect(markup).not.toContain('Проект не найден');
    expect(markup).toContain('Сводку прочитать не удалось.');
  });
});

describe('the page reads the project from the address and from nowhere else', () => {
  it('states «Все проекты» for an address with no ?project=', () => {
    const client = newClient();
    client.setQueryData(queryKeys.dashboard.summary(), ALL);
    const markup = renderScreen(client, atAddress('/dashboard', '', createElement(DashboardPage)));
    expect(visible(markup)).toContain('Охват Все проекты');
  });

  it('states «Все проекты» for an empty ?project=', () => {
    const client = newClient();
    client.setQueryData(queryKeys.dashboard.summary(), ALL);
    const markup = renderScreen(client, atAddress('/dashboard', 'project=', createElement(DashboardPage)));
    expect(visible(markup)).toContain('Охват Все проекты');
  });

  it('states «Все проекты» where no router is mounted (a one-pass render has no address)', () => {
    const client = newClient();
    client.setQueryData(queryKeys.dashboard.summary(), ALL);
    const markup = renderScreen(client, createElement(DashboardPage));
    expect(visible(markup)).toContain('Охват Все проекты');
  });

  it('reads the project of ?project= and states its name', () => {
    const client = newClient();
    client.setQueryData(queryKeys.dashboard.summary(A), ONLY_A);
    const markup = renderScreen(client, atAddress('/dashboard', `project=${A}`, createElement(DashboardPage)));
    expect(visible(markup)).toContain('Охват Проект Альфа');
  });

  it('builds the way out from the address: the project and its own selection go, the other parameters stay', () => {
    const client = newClient();
    seedError(client, queryKeys.dashboard.summary(UNKNOWN), notFound());
    const markup = renderScreen(
      client,
      atAddress('/dashboard', `x=1&project=${UNKNOWN}&section=AR`, createElement(DashboardPage)),
    );
    expect(markup).toContain('Проект не найден');
    expect(markup).toMatch(/<a [^>]*href="\/dashboard\?x=1"[^>]*>Все проекты<\/a>/);
  });

  it('is a bare /dashboard when the project was the only parameter', () => {
    const client = newClient();
    seedError(client, queryKeys.dashboard.summary(UNKNOWN), notFound());
    const markup = renderScreen(
      client,
      atAddress('/dashboard', `project=${UNKNOWN}`, createElement(DashboardPage)),
    );
    expect(markup).toMatch(/<a [^>]*href="\/dashboard"[^>]*>Все проекты<\/a>/);
  });
});

describe('the project reaches the request, and a change of project asks again', () => {
  const read = vi.mocked(getDashboardSummary);
  let live: LiveRender | null = null;

  function answer(data: DashboardSummary): ApiResponse<DashboardSummary> {
    return { data, status: 200, correlationId: 'cid-dashboard' };
  }

  beforeEach(() => {
    read.mockReset();
    read.mockImplementation((async (input: { query?: { project_uid?: string } }) => {
      const project = input.query?.project_uid;
      if (project === undefined) return answer(ALL);
      if (project === A) return answer(ONLY_A);
      if (project === B) return answer(ONLY_B);
      throw notFound();
    }) as unknown as typeof getDashboardSummary);
  });

  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  const page = (client: QueryClient, query: string): ReactElement =>
    createElement(
      QueryClientProvider,
      { client },
      createElement(DashboardEagerSeam.Provider, { value: Dashboard }, atAddress('/dashboard', query, createElement(DashboardPage))),
    );

  const freshClient = (): QueryClient =>
    new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnMount: false, gcTime: Infinity, staleTime: 30_000 } } });

  async function settled(view: LiveRender): Promise<void> {
    for (let round = 0; round < 5; round += 1) {
      await view.settle(() => new Promise<void>((done) => setTimeout(done, 0)));
    }
  }

  it('sends no query at all for «Все проекты»', async () => {
    live = await mountLive(page(freshClient(), ''));
    await settled(live);
    expect(read.mock.calls).toEqual([[{}]]);
    expect(visible(live.markup())).toContain('Охват Все проекты');
  });

  it('sends project_uid for ?project=', async () => {
    live = await mountLive(page(freshClient(), `project=${A}`));
    await settled(live);
    expect(read.mock.calls).toEqual([[{ query: { project_uid: A } }]]);
    expect(visible(live.markup())).toContain('Охват Проект Альфа');
  });

  it('asks again for the new project when the address changes, and shows only the new one', async () => {
    const client = freshClient();
    live = await mountLive(page(client, `project=${A}`));
    await settled(live);
    expect(visible(live.markup())).toContain('Охват Проект Альфа');

    await live.update(page(client, `project=${B}`));
    await settled(live);

    expect(read.mock.calls).toEqual([[{ query: { project_uid: A } }], [{ query: { project_uid: B } }]]);
    expect(visible(live.markup())).toContain('Охват Проект Бета');
    expect(live.markup()).not.toContain('Проект Альфа');
  });

  it('asks again, without a project, when the project leaves the address', async () => {
    const client = freshClient();
    live = await mountLive(page(client, `project=${A}`));
    await settled(live);

    await live.update(page(client, ''));
    await settled(live);

    expect(read.mock.calls).toEqual([[{ query: { project_uid: A } }], [{}]]);
    expect(visible(live.markup())).toContain('Охват Все проекты');
  });

  it('shows «Проект не найден» for a project the server does not know, with the way out', async () => {
    live = await mountLive(page(freshClient(), `project=${UNKNOWN}&x=1`));
    await settled(live);
    expect(read.mock.calls).toEqual([[{ query: { project_uid: UNKNOWN } }]]);
    const markup = live.markup();
    expect(markup).toContain('Проект не найден');
    expect(markup).toContain('href="/dashboard?x=1"');
    expect(markup).not.toContain('Охват');
  });
});
