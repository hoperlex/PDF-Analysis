/**
 * `UIP-S01-01` (Г7-B): the front door's table of sections is counted over the object the screen works in.
 *
 * «Главная» is a screen of class `optional` since this task: `useCurrentProject` (`UIP-G-06`) gives the object the address names
 * (`?project=<uid>`), the explicit «Все объекты» (`?project=all`) or, where the address is silent, the object the account chose last
 * (`getMe`); the container `LazyHomeSections` hands it to `HomeSectionsOverview`. Two instruments, as in
 * `tests/unit/dashboard/dashboard-project.test.ts`: the one-pass render proves WHICH read the table shows (seed one key, and the
 * other key's numbers must not appear), the live mount proves the REQUESTS (the object reaches the read, a change of object asks
 * again, the tiles under the table keep asking for every object) and that the screen does not move when the object does.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PathnameContext, SearchParamsContext } from 'next/dist/shared/lib/hooks-client-context.shared-runtime';
import { createElement } from 'react';
import type { ReactElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, getDashboardSummary: vi.fn(), getMe: vi.fn(), listProjects: vi.fn() };
});

import { HomePage, HomeSectionsEagerSeam } from '@/_pages/home';
import { ApiError, getDashboardSummary, getMe, listProjects, queryKeys } from '@/shared/api';
import type { ApiResponse, DashboardSummary, ErrorEnvelope } from '@/shared/api';
import { PROJECT_SECTIONS } from '@/entities/project';
import { HomeSectionsOverview } from '@/widgets/dashboard';

import { sectionAudit } from './audit-counts';
import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { renderScreen, seedError } from '../screens/harness';
import { LABEL, NO_NEXT, ULID_STEM, account, loaded, summary } from '../screens/home-fixtures';

const A = `prj_${ULID_STEM}A`;
const B = `prj_${ULID_STEM}B`;
const UNKNOWN = `prj_${ULID_STEM}Z`;

/** The section the assertions read: neither the first (no «Не запускались» there) nor the last. */
const SECTION = PROJECT_SECTIONS[1]!;

/**
 * A complete summary whose section `index` holds `base + index` documents, none of them run, so the object a table is counted over
 * can be told from its numbers: every object has its own `base`. `summary()` of the fixtures is `base` 0, «Все объекты».
 */
function counted(base: number): DashboardSummary {
  return summary({
    section_breakdown: [
      ...PROJECT_SECTIONS.map((section, index) => ({
        section: section.code,
        document_count: base + index,
        ...sectionAudit(base + index),
      })),
      { document_count: 5, ...sectionAudit(5) },
    ],
  });
}

const ALL = counted(0);
const ONLY_A = counted(100);
const ONLY_B = counted(200);

function notFound(): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.57.0',
    error_code: 'not_found',
    message: 'Одна безопасная для вызывающей стороны фраза.',
    correlation_id: 'cid-home-404',
    retryable: false,
  };
  return new ApiError(404, envelope, 'cid-home-404');
}

/** The element under the address a router would have mounted: a pathname and a query string. */
function atAddress(query: string, element: ReactElement): ReactElement {
  return createElement(
    PathnameContext.Provider,
    { value: '/' },
    createElement(SearchParamsContext.Provider, { value: new URLSearchParams(query) }, element),
  );
}

const page = (roles: readonly ('expert' | 'admin' | 'viewer')[] = ['viewer']): ReactElement =>
  createElement(HomePage, { displayLabel: LABEL, roles });

/** The text a browser would show: tags stripped. */
function visible(markup: string): string {
  return markup.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
}

/** The `<li>` of one section row. */
function rowOf(markup: string, code: string): string {
  const match = new RegExp(`<li[^>]*data-section="${code}"[^>]*>([\\s\\S]*?)</li>`).exec(markup);
  if (match === null) throw new Error(`no row for ${code}`);
  return match[1] as string;
}

/** The documents of a section row: its bold figure, the first `<strong>` in it. */
function documentsOf(markup: string, code: string): number {
  const figure = /<strong>(\d+)<\/strong>/.exec(rowOf(markup, code));
  if (figure === null) throw new Error(`row ${code} carries no figure`);
  return Number(figure[1]);
}

/** The table of the front door only: the tiles under it carry the all-objects summary and their own numbers. */
function tableOf(markup: string): string {
  const start = markup.indexOf('data-home-sections=""');
  expect(start, 'the table of sections is on the page').toBeGreaterThanOrEqual(0);
  const end = markup.indexOf('</section>', start);
  return markup.slice(start, end);
}

describe('the table is counted over the object the address names (one pass)', () => {
  function seeded(lastProject?: string | null): QueryClient {
    const client = loaded();
    if (lastProject !== undefined) client.setQueryData(queryKeys.account.me(), account(lastProject));
    client.setQueryData(queryKeys.dashboard.summary(A), ONLY_A);
    client.setQueryData(queryKeys.dashboard.summary(B), ONLY_B);
    return client;
  }
  const at = (client: QueryClient, query: string): string => renderScreen(client, atAddress(query, page()));

  it('?project=<uid>: that object\'s numbers, and every row is the link to that object\'s section', () => {
    const table = tableOf(at(seeded(), `project=${A}`));
    expect(table).toContain('data-home-scope="project"');
    expect(documentsOf(table, SECTION.code)).toBe(101);
    for (const section of PROJECT_SECTIONS) {
      const link = new RegExp(`<a [^>]*data-section-open="${section.code}"[^>]*>`).exec(rowOf(table, section.code))?.[0];
      expect(link, section.code).toBeDefined();
      expect(link, section.code).toContain(`href="/projects/${A}/sections/${section.code}"`);
    }
    // The tiles under the table do not follow it: they count every object.
    expect(at(seeded(), `project=${A}`)).toContain(`data-summary-figure="documents">5<`);
  });

  it('the number of «Не запускались» is the link to the section narrowed to those documents', () => {
    const row = rowOf(tableOf(at(seeded(), `project=${A}`)), SECTION.code);
    const link = /<a [^>]*data-not-run-link=""[^>]*>/.exec(row)?.[0];
    expect(link).toBeDefined();
    expect(link).toContain(`href="/projects/${A}/sections/${SECTION.code}?filter=not_run"`);
    // A section with nothing to show has no link: a zero is a plain number (the first section of `ALL` holds no document).
    const empty = loaded();
    empty.setQueryData(queryKeys.dashboard.summary(A), ALL);
    expect(rowOf(tableOf(at(empty, `project=${A}`)), PROJECT_SECTIONS[0]!.code)).not.toContain('data-not-run-link');
  });

  it('?project=all: every object\'s numbers, and a row unfolds its details instead of opening a section', () => {
    const table = tableOf(at(seeded(A), 'project=all'));
    expect(table).toContain('data-home-scope="all"');
    expect(documentsOf(table, SECTION.code)).toBe(1);
    expect(table).not.toContain('data-section-open');
    expect(table).not.toContain('data-section-toggle');
    expect(rowOf(table, SECTION.code)).toMatch(/<button[^>]*aria-expanded="false"/);
  });

  it('a silent address: the account\'s last object, and ?project=<uid> beats it', () => {
    expect(documentsOf(tableOf(at(seeded(A), '')), SECTION.code)).toBe(101);
    expect(documentsOf(tableOf(at(seeded(A), 'project=')), SECTION.code)).toBe(101);
    expect(documentsOf(tableOf(at(seeded(B), 'x=1')), SECTION.code)).toBe(201);
    expect(documentsOf(tableOf(at(seeded(A), `project=${B}`)), SECTION.code)).toBe(201);
  });

  it('no last object (none, absent, not read yet): «Все объекты», drawn at once', () => {
    for (const client of [seeded(null), seeded(undefined), seeded()]) {
      const table = tableOf(at(client, ''));
      expect(table).toContain('data-home-scope="all"');
      expect(documentsOf(table, SECTION.code)).toBe(1);
    }
  });

  it('can fail: the last object does not stand in for an address that chose another object or «Все объекты»', () => {
    expect(documentsOf(tableOf(at(seeded(A), `project=${B}`)), SECTION.code)).not.toBe(101);
    expect(documentsOf(tableOf(at(seeded(A), 'project=all')), SECTION.code)).not.toBe(101);
  });

  it('shows a loading state, not another object\'s numbers, for an object whose summary is not cached', () => {
    const client = loaded();
    client.setQueryData(queryKeys.dashboard.summary(B), ONLY_B);
    const table = tableOf(at(client, `project=${A}`));
    expect(table).toContain('Загрузка: разделы объекта…');
    expect(table).not.toContain('data-panel="per-section-breakdown"');
  });

  it('an object the server does not know is its own state, with the way out to «Все объекты», and never a table of zeros', () => {
    const client = loaded();
    seedError(client, queryKeys.dashboard.summary(UNKNOWN), notFound());
    const table = tableOf(at(client, `project=${UNKNOWN}`));
    expect(table).toContain('Объект не найден');
    expect(table).toMatch(/<a [^>]*href="\/\?project=all"[^>]*>Все объекты<\/a>/);
    expect(table).not.toContain('data-panel="per-section-breakdown"');
    expect(table).not.toContain('Повторить');
  });

  it('the same refusal for «Все объекты» is the generic read failure, not an unknown object', () => {
    const client = loaded();
    seedError(client, queryKeys.dashboard.summary(), notFound());
    const table = tableOf(at(client, 'project=all'));
    expect(table).not.toContain('Объект не найден');
    expect(table).toContain('Сводку прочитать не удалось.');
  });
});

describe('the container hands the object to the overview, and the overview reads no address', () => {
  it('the overview takes the object as a property: with none it is «Все объекты»', () => {
    const client = loaded();
    client.setQueryData(queryKeys.dashboard.summary(A), ONLY_A);
    const bare = renderScreen(client, createElement(HomeSectionsOverview));
    expect(bare).toContain('data-home-scope="all"');
    expect(documentsOf(bare, SECTION.code)).toBe(1);
    const named = renderScreen(client, createElement(HomeSectionsOverview, { projectUid: A }));
    expect(named).toContain('data-home-scope="project"');
    expect(documentsOf(named, SECTION.code)).toBe(101);
  });

  it('a page rendered with no router at all (the instruments\' one pass) is «Все объекты»', () => {
    const table = tableOf(renderScreen(loaded(), page()));
    expect(table).toContain('data-home-scope="all"');
  });
});

describe('the requests, and a screen that stays where it is (live mount)', () => {
  const read = vi.mocked(getDashboardSummary);
  const me = vi.mocked(getMe);
  const projects = vi.mocked(listProjects);
  let live: LiveRender | null = null;

  const answer = <T,>(data: T): ApiResponse<T> => ({ data, status: 200, correlationId: 'cid-home' });

  beforeEach(() => {
    me.mockReset();
    me.mockImplementation((async () => answer(account(null))) as unknown as typeof getMe);
    projects.mockReset();
    projects.mockImplementation((async () => answer({ items: [], page: NO_NEXT })) as unknown as typeof listProjects);
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

  const front = (client: QueryClient, query: string): ReactElement =>
    createElement(
      QueryClientProvider,
      { client },
      createElement(HomeSectionsEagerSeam.Provider, { value: HomeSectionsOverview }, atAddress(query, page())),
    );

  const freshClient = (): QueryClient =>
    new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnMount: false, gcTime: Infinity, staleTime: 30_000 } } });

  async function settled(view: LiveRender): Promise<void> {
    for (let round = 0; round < 5; round += 1) {
      await view.settle(() => new Promise<void>((done) => setTimeout(done, 0)));
    }
  }

  /** The `project_uid` of each summary read, in a stable order; `null` is the read of every object. */
  const asked = (): (string | null)[] =>
    read.mock.calls
      .map(([input]) => (input as { query?: { project_uid?: string } }).query?.project_uid ?? null)
      .sort((x, y) => (x ?? '').localeCompare(y ?? ''));

  it('with an object in the address: the table asks for that object, and the tiles keep asking for every object (one read each)', async () => {
    live = await mountLive(front(freshClient(), `project=${A}`));
    await settled(live);
    expect(asked()).toEqual([null, A]);
    expect(documentsOf(tableOf(live.markup()), SECTION.code)).toBe(101);
    // The account is not asked where the address already names the object.
    expect(me).not.toHaveBeenCalled();
  });

  it('with «Все объекты»: one read for the table and the tiles together, and no account read', async () => {
    live = await mountLive(front(freshClient(), 'project=all'));
    await settled(live);
    expect(asked()).toEqual([null]);
    expect(me).not.toHaveBeenCalled();
    expect(tableOf(live.markup())).toContain('data-home-scope="all"');
  });

  it('a silent address: the table moves to the account\'s last object when getMe answers', async () => {
    me.mockImplementation((async () => answer(account(A))) as unknown as typeof getMe);
    live = await mountLive(front(freshClient(), ''));
    await settled(live);
    expect(me).toHaveBeenCalledTimes(1);
    expect(asked()).toEqual([null, A]);
    expect(documentsOf(tableOf(live.markup()), SECTION.code)).toBe(101);
  });

  it('a change of object in the strip changes the table and leaves the screen: the same page, the other object\'s numbers, one more read', async () => {
    const client = freshClient();
    live = await mountLive(front(client, `project=${A}`));
    await settled(live);
    expect(live.markup()).toContain('data-screen="home"');

    await live.update(front(client, `project=${B}`));
    await settled(live);

    expect(asked()).toEqual([null, A, B]);
    expect(live.markup()).toContain('data-screen="home"');
    expect(documentsOf(tableOf(live.markup()), SECTION.code)).toBe(201);
    expect(tableOf(live.markup())).toContain(`href="/projects/${B}/sections/${SECTION.code}"`);
    expect(tableOf(live.markup())).not.toContain(`/projects/${A}/`);

    await live.update(front(client, 'project=all'));
    await settled(live);
    // Every object's summary is already held (the tiles read it), so «Все объекты» asks for nothing more.
    expect(asked()).toEqual([null, A, B]);
    expect(live.markup()).toContain('data-screen="home"');
    expect(documentsOf(tableOf(live.markup()), SECTION.code)).toBe(1);
  });

  it('an account whose getMe failed stays on «Все объекты», as the dashboard does', async () => {
    me.mockReset();
    me.mockRejectedValue(notFound());
    live = await mountLive(front(freshClient(), ''));
    await settled(live);
    expect(asked()).toEqual([null]);
    expect(visible(tableOf(live.markup()))).toContain('Разделы объекта');
    expect(tableOf(live.markup())).toContain('data-home-scope="all"');
  });
});
