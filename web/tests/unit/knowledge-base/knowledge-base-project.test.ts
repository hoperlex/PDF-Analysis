/**
 * «База знаний» follows the project in the address (`UI-PARITY-01`, «Project context»).
 *
 * The screen is class `optional`: without `?project=` it reads the whole journal and states «Все
 * проекты»; with one it sends `project_uid`, states the project and how many entries match
 * (`total`, not the length of the page), and a change of project returns to the first page as a
 * change of filter does. An unknown project is an empty page with `total: 0`, and the screen shows
 * the uid it was given and the empty state of a selection, with «Все проекты» as the way out — it does
 * not claim the project exists, and it does not claim that the installation has no decision (`D-313`).
 *
 * Mounted live (`analysis-settings/live-render.ts`) under a mounted address, because a project
 * change and a press are events the one-pass render cannot deliver. Only the transport is replaced.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PathnameContext, SearchParamsContext } from 'next/dist/shared/lib/hooks-client-context.shared-runtime';
import { createElement } from 'react';
import type { ReactElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, listDecisions: vi.fn(), listProjects: vi.fn() };
});

import { KnowledgeBaseEagerSeam, KnowledgeBasePage } from '@/_pages/knowledge-base';
import { listDecisions, listProjects } from '@/shared/api';
import type { ApiResponse, DecisionRecord, DecisionRecordPage } from '@/shared/api';
import { JOURNAL_PAGE_LIMIT } from '@/entities/expert-decision';
import { KnowledgeBase } from '@/widgets/knowledge-base';

import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import '../review/fixtures';

const ULID = '01M2545JSD15ETSNNV904X991F';
const A = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const B = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8C';
const UNKNOWN = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8D';
const LISTED_ONLY = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8E';

function record(n: number, project: string, name: string, over: Partial<DecisionRecord> = {}): DecisionRecord {
  return {
    decision_id: `dec_01M2545JSD15ETSNNV904X9${String(n).padStart(3, '0')}`,
    finding_uid: `fnd_${ULID}`,
    finding_observation_id: `fobs_${ULID}`,
    event_type: 'accept',
    verdict: 'accepted',
    comment: null,
    author_label: 'проверяющий',
    recorded_at: '2026-09-10T09:00:00.000Z',
    project_uid: project,
    run_id: `run_${ULID}`,
    document_uid: `doc_${ULID}`,
    version_uid: `ver_${ULID}`,
    project_name: name,
    document_name: 'АР-1',
    section: 'AR',
    category: 'internal_contradiction',
    finding_text: `Решение номер ${n}`,
    current_verdict: 'accepted',
    decision_event_count: 1,
    ...over,
  };
}

const ALL_P1 = [record(1, A, 'Проект Альфа'), record(2, B, 'Проект Бета')];
const A_P1 = [record(11, A, 'Проект Альфа'), record(12, A, 'Проект Альфа')];
const A_P2 = [record(13, A, 'Проект Альфа')];
/** A record of a version no expert has classified yet: `section` is absent, not empty. */
function unclassified(source: DecisionRecord): DecisionRecord {
  const { section, ...rest } = source;
  void section;
  return rest;
}

const B_P1 = [unclassified(record(21, B, 'Проект Бета'))];

function answer(items: DecisionRecord[], next: string | null, total: number): ApiResponse<DecisionRecordPage> {
  return { data: { items, page: { next_cursor: next }, total }, status: 200, correlationId: 'cid-kb' };
}

type Query = { category?: string; verdict?: string; cursor?: string; limit?: number; project_uid?: string };

const journal = vi.mocked(listDecisions);
const projects = vi.mocked(listProjects);
const everyQuery = (): Query[] => journal.mock.calls.map((call) => (call[0] as { query: Query }).query);
/**
 * The journal's own pages. The verdict chips (`UI-B-32`) read `total` with `limit=1` beside them; those four reads are
 * asserted in `knowledge-base-verdict-chips.test.ts`, and are left out here so these tests keep naming the list's reads.
 */
const queries = (): Query[] => everyQuery().filter((query) => query.limit !== 1);

beforeEach(() => {
  journal.mockReset();
  journal.mockImplementation((async (input: { query: Query }) => {
    const { project_uid: project, cursor } = input.query;
    if (project === undefined) return answer(ALL_P1, null, 120);
    if (project === A) return cursor === 'cursor-a1' ? answer(A_P2, null, 3) : answer(A_P1, 'cursor-a1', 3);
    if (project === B) return answer(B_P1, null, 1);
    // A project the server does not know, or one with no decisions: an empty page, not an error.
    return answer([], null, 0);
  }) as unknown as typeof listDecisions);

  projects.mockReset();
  projects.mockImplementation((async () => ({
    data: {
      items: [{ project_uid: LISTED_ONLY, name: 'Проект из списка', created_at: '2026-09-10T08:00:00.000Z' }],
      page: { next_cursor: null },
    },
    status: 200,
    correlationId: 'cid-projects',
  })) as unknown as typeof listProjects);
});

/** The page under an address: a pathname and a query string, as a router would have mounted. */
function page(client: QueryClient, query: string): ReactElement {
  return createElement(
    QueryClientProvider,
    { client },
    createElement(
      KnowledgeBaseEagerSeam.Provider,
      { value: KnowledgeBase },
      createElement(
        PathnameContext.Provider,
        { value: '/knowledge-base' },
        createElement(SearchParamsContext.Provider, { value: new URLSearchParams(query) }, createElement(KnowledgeBasePage)),
      ),
    ),
  );
}

const freshClient = (): QueryClient =>
  new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnMount: false, gcTime: Infinity, staleTime: 30_000 } } });

async function settled(view: LiveRender): Promise<void> {
  for (let round = 0; round < 5; round += 1) {
    await view.settle(() => new Promise<void>((done) => setTimeout(done, 0)));
  }
}

async function press(view: LiveRender, label: string): Promise<boolean> {
  const delivered = await view.press(label);
  await settled(view);
  return delivered;
}

/** The text a browser would show: tags stripped. */
function visible(markup: string): string {
  return markup.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
}

describe('the project reaches the request', () => {
  let live: LiveRender | null = null;
  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  async function mountAt(query: string, client = freshClient()): Promise<LiveRender> {
    live = await mountLive(page(client, query));
    await settled(live);
    return live;
  }

  it('sends no project_uid for «Все проекты»', async () => {
    const view = await mountAt('');
    expect(queries()).toEqual([{ limit: JOURNAL_PAGE_LIMIT }]);
    expect(view.markup()).toContain('data-journal-scope="all"');
    expect(visible(view.markup())).toContain('Охват Все проекты');
  });

  it('sends no project_uid for an empty ?project=', async () => {
    await mountAt('project=');
    expect(queries()).toEqual([{ limit: JOURNAL_PAGE_LIMIT }]);
  });

  it('sends project_uid for ?project=, beside the filters', async () => {
    await mountAt(`project=${A}`);
    expect(queries()).toEqual([{ project_uid: A, limit: JOURNAL_PAGE_LIMIT }]);
  });

  it('keeps project_uid on every page of the walk', async () => {
    const view = await mountAt(`project=${A}`);
    expect(await press(view, 'Далее')).toBe(true);
    expect(queries()).toEqual([
      { project_uid: A, limit: JOURNAL_PAGE_LIMIT },
      { project_uid: A, limit: JOURNAL_PAGE_LIMIT, cursor: 'cursor-a1' },
    ]);
    expect(view.markup()).toContain('Решение номер 13<');
  });
});

describe('the screen states its scope and how many entries match', () => {
  let live: LiveRender | null = null;
  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  async function mountAt(query: string): Promise<LiveRender> {
    live = await mountLive(page(freshClient(), query));
    await settled(live);
    return live;
  }

  it('says «N записей» from total, not from the length of the page on screen', async () => {
    const view = await mountAt('');
    expect(ALL_P1).toHaveLength(2);
    expect(visible(view.markup())).toContain('120 записей');
    expect(view.markup()).toContain('data-journal-total="120"');
  });

  it('says the project’s name, from the records the server sent, with the project’s own total', async () => {
    const view = await mountAt(`project=${A}`);
    expect(view.markup()).toContain('data-journal-scope="project"');
    expect(visible(view.markup())).toContain('Охват Проект Альфа 3 записи');
    expect(view.markup()).not.toContain('Все проекты');
  });

  it('declines the noun with the number', async () => {
    journal.mockImplementation((async () => answer(ALL_P1, null, 1)) as unknown as typeof listDecisions);
    expect(visible((await mountAt('')).markup())).toContain('1 запись');
  });

  it('says «0 записей» and the empty state of a selection for a project with nothing in it, by the uid it was given', async () => {
    const view = await mountAt(`project=${UNKNOWN}`);
    const text = visible(view.markup());
    expect(text).toContain(`Охват ${UNKNOWN} 0 записей`);
    expect(text).toContain('По выбранному отбору решений нет');
    // It says nothing about the installation: a project with no decision is not an installation with none (D-313).
    expect(text).not.toContain('Решений пока нет');
    expect(text).not.toContain('ещё не принято ни одного решения');
    // It does not claim the project exists: no name was found for it anywhere.
    expect(text).not.toContain('Проект Альфа');
    // The scope line still names the project. «Все проекты» is the way out below it, once, as a link to the unfiltered screen.
    expect(text).not.toContain('Охват Все проекты');
    expect(text.match(/Все проекты/g)).toHaveLength(1);
    expect(view.markup()).toMatch(/<a [^>]*href="\/knowledge-base"[^>]*>Все проекты<\/a>/);
    // Only the project narrows the list, so there is no category or verdict to reset.
    expect(text).not.toContain('Сбросить категорию и вердикт');
  });

  it('says a known project’s name from the project list when it has no decisions to carry the name', async () => {
    const view = await mountAt(`project=${LISTED_ONLY}`);
    const text = visible(view.markup());
    expect(text).toContain('Охват Проект из списка 0 записей');
    expect(text).toContain('По выбранному отбору решений нет');
    expect(text).not.toContain('ещё не принято ни одного решения');
  });

  it('does not read the project list for «Все проекты»', async () => {
    await mountAt('');
    expect(projects).not.toHaveBeenCalled();
  });
});

// `UI-B-34`: the page opens on the original's table, as the original does; the events are one press away and cost no read.
describe('the page opens on the table', () => {
  let live: LiveRender | null = null;
  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  it('draws the table with the project and the section in their own cells, and the events after a press, with no further read', async () => {
    live = await mountLive(page(freshClient(), ''));
    await settled(live);
    expect(live.markup()).toContain('data-knowledge-base-table');
    expect(live.markup()).not.toContain('class="am-kb__record"');
    expect(live.markup()).toMatch(/<button[^>]*aria-pressed="true"[^>]*data-kb-view="table"/);
    expect(visible(live.markup())).toContain('Проект Альфа АР-1');
    const reads = queries().length;
    expect(await press(live, 'События')).toBe(true);
    expect(live.markup()).toContain('class="am-kb__record"');
    expect(live.markup()).not.toContain('data-knowledge-base-table');
    expect(await press(live, 'Таблица')).toBe(true);
    expect(live.markup()).toContain('data-knowledge-base-table');
    expect(queries()).toHaveLength(reads);
  });

  it('keeps the page’s paging and its project in the table: the next page is another table of the same project', async () => {
    live = await mountLive(page(freshClient(), `project=${A}`));
    await settled(live);
    expect(await press(live, 'Далее')).toBe(true);
    expect(live.markup()).toContain('data-knowledge-base-table');
    expect(live.markup()).toContain('Решение номер 13<');
  });
});

// `UI-B-34`: the page opens on the original's table; the place line «Проект · Документ · Раздел» is the events view's, one press away.
describe('each record says where it belongs, in the events view', () => {
  let live: LiveRender | null = null;
  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  it('prints «Проект · Документ · Раздел» with the section’s name from the catalogue', async () => {
    live = await mountLive(page(freshClient(), ''));
    await settled(live);
    await press(live, 'События');
    expect(visible(live.markup())).toContain('Проект Альфа · АР-1 · Архитектурные решения (АР)');
  });

  it('drops the section, and invents no label for its absence, when the version is not classified', async () => {
    live = await mountLive(page(freshClient(), `project=${B}`));
    await settled(live);
    await press(live, 'События');
    const text = visible(live.markup());
    expect(text).toContain('Проект Бета · АР-1');
    expect(text).not.toContain('Проект Бета · АР-1 ·');
    expect(text).not.toContain('Без раздела');
  });
});

describe('an empty page under a selection is about the selection, and the way back is on the screen (D-313)', () => {
  let live: LiveRender | null = null;
  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  /** The default answers, except that a category of `dimensions` or a verdict of `rejected` matches nothing. */
  function nothingFor(category: string | null, verdict: string | null): void {
    const everything = journal.getMockImplementation() as unknown as ((input: { query: Query }) => Promise<unknown>) | undefined;
    expect(everything).toBeDefined();
    journal.mockImplementation(((input: { query: Query }) =>
      (category !== null && input.query.category === category) || (verdict !== null && input.query.verdict === verdict)
        ? Promise.resolve(answer([], null, 0))
        : everything!(input)) as unknown as typeof listDecisions);
  }

  async function mountAt(query: string): Promise<LiveRender> {
    live = await mountLive(page(freshClient(), query));
    await settled(live);
    return live;
  }

  async function change(view: LiveRender, label: string, value: string): Promise<boolean> {
    const delivered = await view.change(label, value);
    await settled(view);
    return delivered;
  }

  it('keeps the installation sentence for a journal that is empty with no category, verdict or project', async () => {
    journal.mockImplementation((async () => answer([], null, 0)) as unknown as typeof listDecisions);
    const view = await mountAt('');
    const text = visible(view.markup());
    expect(text).toContain('Решений пока нет');
    expect(text).toContain('В этой установке ещё не принято ни одного решения');
    expect(text).not.toContain('По выбранному отбору');
    expect(text).not.toContain('Сбросить категорию и вердикт');
    expect(view.markup()).toContain('data-knowledge-base-empty="installation"');
  });

  it('says it is the selection when a category matches nothing, and the button resets category and verdict together', async () => {
    // Both the category and the verdict match nothing, so a reset that cleared only one of them would still show an empty page.
    nothingFor('dimensions', 'accepted');
    const view = await mountAt('');
    expect(visible(view.markup())).toContain('Решение номер 1');
    expect(await change(view, 'Категория', 'dimensions')).toBe(true);
    const text = visible(view.markup());
    expect(text).toContain('По выбранному отбору решений нет');
    expect(text).not.toContain('ещё не принято ни одного решения');
    expect(text).not.toContain('Решений пока нет');
    // No project is chosen, so there is no «Все проекты» to offer: the words appear once, in the scope line, and are no link.
    expect(text.match(/Все проекты/g)).toHaveLength(1);
    expect(view.markup()).not.toMatch(/<a [^>]*>Все проекты<\/a>/);

    // A verdict as well, so that the reset is seen to clear both.
    await change(view, 'Вердикт', 'accepted');
    expect(visible(view.markup())).toContain('По выбранному отбору решений нет');
    expect(await press(view, 'Сбросить категорию и вердикт')).toBe(true);

    const after = visible(view.markup());
    expect(after).toContain('Решение номер 1');
    expect(after).not.toContain('По выбранному отбору');
    // Both filters are back on «Любая категория» and «Любой вердикт»: pressing the button once cleared the two.
    expect(view.count('Сбросить категорию и вердикт')).toBe(0);
  });

  it('offers «Все проекты» with the rest of the address kept, beside the reset, when a project and a verdict are on', async () => {
    nothingFor(null, 'rejected');
    // `foo` is kept; `tab` is one of the parameters that only meant something inside the old project and goes with it.
    const view = await mountAt(`project=${A}&foo=bar&tab=x`);
    expect(await change(view, 'Вердикт', 'rejected')).toBe(true);
    const text = visible(view.markup());
    expect(text).toContain('По выбранному отбору решений нет');
    expect(text).toContain('Сбросить категорию и вердикт');
    expect(text.match(/Все проекты/g)).toHaveLength(1);
    expect(view.markup()).toMatch(/<a [^>]*href="\/knowledge-base\?foo=bar"[^>]*>Все проекты<\/a>/);
    // The scope line still states the project the reader is in. An empty page carries no record to name it, and the project list
    // does not hold it, so the line shows the uid it was given, as it does for any project the page cannot name.
    expect(view.markup()).toContain('data-journal-scope="project"');
    expect(text).toContain(`Охват ${A} 0 записей`);
  });

  it('resets from the empty state back to the project’s own first page, not to «Все проекты»', async () => {
    nothingFor('dimensions', null);
    const view = await mountAt(`project=${A}`);
    await change(view, 'Категория', 'dimensions');
    expect(visible(view.markup())).toContain('По выбранному отбору решений нет');
    await press(view, 'Сбросить категорию и вердикт');
    const text = visible(view.markup());
    expect(text).toContain('Решение номер 11');
    expect(text).toContain('Охват Проект Альфа');
    expect(text).not.toContain('Охват Все проекты');
  });
});

describe('a change of project returns to the first page', () => {
  let live: LiveRender | null = null;
  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  it('asks the new project with NO cursor, and has nowhere to go back to', async () => {
    const client = freshClient();
    live = await mountLive(page(client, `project=${A}`));
    await settled(live);
    await press(live, 'Далее');
    expect(live.markup()).toContain('Решение номер 13<');
    journal.mockClear();

    await live.update(page(client, `project=${B}`));
    await settled(live);

    expect(queries()).toEqual([{ project_uid: B, limit: JOURNAL_PAGE_LIMIT }]);
    expect(live.markup()).toContain('Решение номер 21<');
    expect(live.count('Назад')).toBe(0);
  });

  it('never asks the new project with the old project’s cursor, not even once', async () => {
    const client = freshClient();
    live = await mountLive(page(client, `project=${A}`));
    await settled(live);
    await press(live, 'Далее');
    journal.mockClear();

    await live.update(page(client, `project=${B}`));
    await settled(live);

    expect(queries().every((query) => query.cursor === undefined)).toBe(true);
  });

  it('opens the first page, not the old second page, when the reader returns to the project', async () => {
    const client = freshClient();
    live = await mountLive(page(client, `project=${A}`));
    await settled(live);
    await press(live, 'Далее');
    expect(live.markup()).toContain('Решение номер 13<');

    await live.update(page(client, `project=${B}`));
    await settled(live);
    await live.update(page(client, `project=${A}`));
    await settled(live);

    expect(live.markup()).toContain('Решение номер 11<');
    expect(live.markup()).not.toContain('Решение номер 13<');
    // The first page of A has a «Далее», so the pager is drawn; «Назад» is there and cannot be pressed.
    expect(await press(live, 'Назад')).toBe(false);
  });

  it('also returns to the first page when the project leaves the address', async () => {
    const client = freshClient();
    live = await mountLive(page(client, `project=${A}`));
    await settled(live);
    await press(live, 'Далее');
    journal.mockClear();

    await live.update(page(client, ''));
    await settled(live);

    expect(queries()).toEqual([{ limit: JOURNAL_PAGE_LIMIT }]);
    expect(live.count('Назад')).toBe(0);
  });

  it('can fail: a project that does NOT change keeps its place', async () => {
    const client = freshClient();
    live = await mountLive(page(client, `project=${A}`));
    await settled(live);
    await press(live, 'Далее');

    await live.update(page(client, `project=${A}`));
    await settled(live);

    expect(live.markup()).toContain('Решение номер 13<');
    expect(live.count('Назад')).toBe(1);
  });
});
