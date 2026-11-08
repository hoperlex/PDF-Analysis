/**
 * `D-372`: «База знаний» keeps its type, view, category and verdict in the address (`?kind=&view=&category=&verdict=`), so a saved link,
 * a reload and the side menu's «База знаний» (no query) return to the same filter, as «Очередь» does.
 *
 * Held here, each with a case that shows it can fail:
 *
 *   - the address is read and written as a pure pair against the closed sets: a value outside them is the default and is never echoed,
 *     the default of each is the ABSENT parameter, and a parameter that is not this screen's (`project`) is carried through;
 *   - the page opened on an address makes its first reads already filtered, and shows the filter in its controls;
 *   - a press on a chip, a change of the select and a press on «События» write the address (replacing the entry) and the page follows;
 *   - a navigation to another address (a link, the menu) changes the filter, and a stack of cursors walked under the old filter is not
 *     used for the new one.
 *
 * Mounted live under `routed-address.ts`, which gives the page an address that follows what it writes.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import type { ReactElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, listDecisions: vi.fn(), listProjects: vi.fn() };
});

import { KnowledgeBaseEagerSeam, KnowledgeBasePage } from '@/_pages/knowledge-base';
import { DEFAULT_KB_ADDRESS, readKbAddress, writeKbAddress } from '@/_pages/knowledge-base/model/address';
import { listDecisions, listProjects } from '@/shared/api';
import type { ApiResponse, DecisionRecord, DecisionRecordPage } from '@/shared/api';
import { JOURNAL_PAGE_LIMIT } from '@/entities/expert-decision';
import { KnowledgeBase } from '@/widgets/knowledge-base';

import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import '../review/fixtures';
import { RoutedAddress, currentSearch } from './routed-address';

const ULID = '01M2545JSD15ETSNNV904X991F';

function record(n: number): DecisionRecord {
  return {
    decision_id: `dec_01M2545JSD15ETSNNV904X9${String(n).padStart(3, '0')}`,
    finding_uid: `fnd_${ULID}`,
    finding_observation_id: `fobs_${ULID}`,
    event_type: 'accept',
    verdict: 'accepted',
    comment: null,
    author_label: 'проверяющий',
    recorded_at: '2026-09-10T09:00:00.000Z',
    project_uid: `prj_${ULID}`,
    run_id: `run_${ULID}`,
    document_uid: `doc_${ULID}`,
    version_uid: `ver_${ULID}`,
    project_name: 'Проект Альфа',
    document_name: 'АР-1',
    category: 'internal_contradiction',
    finding_text: `Решение номер ${n}`,
    current_verdict: 'accepted',
    decision_event_count: 1,
  };
}

function answer(items: DecisionRecord[], next: string | null, total: number): ApiResponse<DecisionRecordPage> {
  return { data: { items, page: { next_cursor: next }, total }, status: 200, correlationId: 'cid-address' };
}

type Query = { category?: string; verdict?: string; cursor?: string; limit?: number };

const journal = vi.mocked(listDecisions);
const projects = vi.mocked(listProjects);
/** The list's own pages (the chips read `limit=1` beside them). */
const listQueries = (): Query[] =>
  journal.mock.calls.map((call) => (call[0] as { query: Query }).query).filter((query) => query.limit !== 1);

beforeEach(() => {
  journal.mockReset();
  journal.mockImplementation((async (input: { query: Query }) => {
    const query = input.query;
    if (query.limit === 1) return answer([record(1)], null, 10);
    if (query.cursor === 'cursor-1') return answer([record(3), record(4)], null, 4);
    return answer([record(1), record(2)], 'cursor-1', 4);
  }) as unknown as typeof listDecisions);
  projects.mockReset();
  projects.mockImplementation((async () => ({
    data: { items: [], page: { next_cursor: null } },
    status: 200,
    correlationId: 'cid-projects',
  })) as unknown as typeof listProjects);
});

const read = (query: string) => readKbAddress(new URLSearchParams(query));
const write = (query: string, next: Parameters<typeof writeKbAddress>[1]) => writeKbAddress(new URLSearchParams(query), next).toString();

describe('the knowledge-base address, read', () => {
  it('names the type, the view and the two filters; an empty address is the first screen of the application', () => {
    expect(read('kind=proposals&view=events&category=dimensions&verdict=accepted')).toEqual({
      kind: 'proposals', view: 'events', category: 'dimensions', verdict: 'accepted',
    });
    expect(read('')).toEqual(DEFAULT_KB_ADDRESS);
    expect(read('kind=&view=&category=&verdict=')).toEqual(DEFAULT_KB_ADDRESS);
    expect(DEFAULT_KB_ADDRESS).toEqual({ kind: 'findings', view: 'table', category: 'all', verdict: 'all' });
  });

  it('drops a value outside the closed sets instead of echoing it', () => {
    expect(read('kind=everything&view=cards&category=weather&verdict=needs_manual_review')).toEqual(DEFAULT_KB_ADDRESS);
    expect(read('verdict=ACCEPTED').verdict).toBe('all');
    expect(read('category=all&verdict=all')).toEqual(DEFAULT_KB_ADDRESS);
  });
});

describe('the knowledge-base address, written', () => {
  it('writes what is not the default, and the default is the absent parameter', () => {
    expect(write('', { ...DEFAULT_KB_ADDRESS, verdict: 'rejected', view: 'events' })).toBe('view=events&verdict=rejected');
    expect(write('verdict=rejected&view=events', DEFAULT_KB_ADDRESS)).toBe('');
    expect(write('', { ...DEFAULT_KB_ADDRESS, kind: 'all' })).toBe('kind=all');
  });

  it('carries the project and any other parameter through', () => {
    expect(write('project=prj_X&foo=bar', { ...DEFAULT_KB_ADDRESS, category: 'dimensions' })).toBe('project=prj_X&foo=bar&category=dimensions');
    expect(write('project=prj_X&verdict=pending', DEFAULT_KB_ADDRESS)).toBe('project=prj_X');
  });

  it('round-trips every value of every parameter', () => {
    for (const kind of ['all', 'findings', 'proposals'] as const) {
      for (const verdict of ['all', 'accepted', 'rejected', 'pending'] as const) {
        const next = { ...DEFAULT_KB_ADDRESS, kind, verdict, view: 'events' as const, category: 'roof' as const };
        expect(read(write('', next))).toEqual(next);
      }
    }
  });
});

describe('the page follows the address', () => {
  let live: LiveRender | null = null;
  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  const freshClient = (): QueryClient =>
    new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnMount: false, gcTime: Infinity, staleTime: 30_000 } } });

  function page(client: QueryClient, query: string): ReactElement {
    return createElement(
      QueryClientProvider,
      { client },
      createElement(
        KnowledgeBaseEagerSeam.Provider,
        { value: KnowledgeBase },
        createElement(RoutedAddress, { query }, createElement(KnowledgeBasePage)),
      ),
    );
  }

  async function settled(view: LiveRender): Promise<void> {
    for (let round = 0; round < 5; round += 1) {
      await view.settle(() => new Promise<void>((done) => setTimeout(done, 0)));
    }
  }

  async function mountAt(query: string, client = freshClient()): Promise<{ view: LiveRender; client: QueryClient }> {
    live = await mountLive(page(client, query));
    await settled(live);
    return { view: live, client };
  }

  it('opens on the filter the address names, with no unfiltered read before it', async () => {
    const { view } = await mountAt('category=dimensions&verdict=accepted');
    expect(listQueries()).toEqual([{ category: 'dimensions', verdict: 'accepted', limit: JOURNAL_PAGE_LIMIT }]);
    // A live select keeps its value as a property, not as markup: the verdict chip is what shows the filter, the request what sent it.
    expect(view.markup()).toMatch(/aria-pressed="true"[^>]*data-kb-verdict="accepted"/);
    expect(view.markup()).toMatch(/aria-pressed="false"[^>]*data-kb-verdict="all"/);
  });

  it('writes a chosen verdict onto the address, replacing the entry, and takes it off again with «Все»', async () => {
    const { view } = await mountAt('project=prj_X');
    await view.press('Отклонено 10');
    await settled(view);
    expect(currentSearch()).toBe('project=prj_X&verdict=rejected');
    expect(listQueries().at(-1)).toEqual({ verdict: 'rejected', limit: JOURNAL_PAGE_LIMIT, project_uid: 'prj_X' });
    await view.press('Все 10');
    await settled(view);
    expect(currentSearch()).toBe('project=prj_X');
  });

  it('writes the category and the view, and the select and the buttons show them', async () => {
    const { view } = await mountAt('');
    await view.change('Категория', 'roof');
    await settled(view);
    expect(currentSearch()).toBe('category=roof');
    await view.press('События');
    await settled(view);
    expect(currentSearch()).toBe('category=roof&view=events');
    expect(view.markup()).toMatch(/aria-pressed="true"[^>]*data-kb-view="events"/);
  });

  it('writes the type, and «Замечания» is the absent parameter', async () => {
    const { view } = await mountAt('');
    await view.press('Все');
    await settled(view);
    expect(currentSearch()).toBe('kind=all');
    await view.press('Замечания');
    await settled(view);
    expect(currentSearch()).toBe('');
  });

  it('follows a navigation: another address is another filter, and the side menu’s plain address clears it', async () => {
    const client = freshClient();
    const { view } = await mountAt('verdict=rejected', client);
    expect(view.markup()).toMatch(/aria-pressed="true"[^>]*data-kb-verdict="rejected"/);
    await view.update(page(client, ''));
    await settled(view);
    expect(view.markup()).toMatch(/aria-pressed="true"[^>]*data-kb-verdict="all"/);
  });

  it('does not use a cursor walked under the old filter for the new one', async () => {
    const client = freshClient();
    const { view } = await mountAt('', client);
    await view.press('Далее');
    await settled(view);
    expect(listQueries().at(-1)).toEqual({ limit: JOURNAL_PAGE_LIMIT, cursor: 'cursor-1' });
    journal.mockClear();
    // A link to another filter: the page walked past is forgotten, whatever pressed nothing.
    await view.update(page(client, 'verdict=pending'));
    await settled(view);
    expect(listQueries()).toEqual([{ verdict: 'pending', limit: JOURNAL_PAGE_LIMIT }]);
    expect(listQueries().every((query) => query.cursor === undefined)).toBe(true);
  });
});
