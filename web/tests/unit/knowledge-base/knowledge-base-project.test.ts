/**
 * «База знаний» follows the project in the address (`UI-PARITY-01`, «Project context»).
 *
 * The screen is class `optional`: without `?project=` it reads the whole journal and states «Все
 * проекты»; with one it sends `project_uid`, states the project and how many entries match
 * (`total`, not the length of the page), and a change of project returns to the first page as a
 * change of filter does. An unknown project is an empty page with `total: 0`, and the screen shows
 * the uid it was given and the existing empty state — it does not claim the project exists.
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
const queries = (): Query[] => journal.mock.calls.map((call) => (call[0] as { query: Query }).query);

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

  it('says «0 записей» and the existing empty state for a project with nothing in it, by the uid it was given', async () => {
    const view = await mountAt(`project=${UNKNOWN}`);
    const text = visible(view.markup());
    expect(text).toContain(`Охват ${UNKNOWN} 0 записей`);
    expect(text).toContain('Решений пока нет');
    // It does not claim the project exists: no name was found for it anywhere.
    expect(text).not.toContain('Проект Альфа');
    expect(text).not.toContain('Все проекты');
  });

  it('says a known project’s name from the project list when it has no decisions to carry the name', async () => {
    const view = await mountAt(`project=${LISTED_ONLY}`);
    const text = visible(view.markup());
    expect(text).toContain('Охват Проект из списка 0 записей');
    expect(text).toContain('Решений пока нет');
  });

  it('does not read the project list for «Все проекты»', async () => {
    await mountAt('');
    expect(projects).not.toHaveBeenCalled();
  });
});

describe('each record says where it belongs', () => {
  let live: LiveRender | null = null;
  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  it('prints «Проект · Документ · Раздел» with the section’s name from the catalogue', async () => {
    live = await mountLive(page(freshClient(), ''));
    await settled(live);
    expect(visible(live.markup())).toContain('Проект Альфа · АР-1 · Архитектурные решения (АР)');
  });

  it('drops the section, and invents no label for its absence, when the version is not classified', async () => {
    live = await mountLive(page(freshClient(), `project=${B}`));
    await settled(live);
    const text = visible(live.markup());
    expect(text).toContain('Проект Бета · АР-1');
    expect(text).not.toContain('Проект Бета · АР-1 ·');
    expect(text).not.toContain('Без раздела');
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
