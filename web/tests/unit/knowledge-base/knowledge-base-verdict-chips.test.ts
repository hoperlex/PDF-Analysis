/**
 * `UI-B-32`, `UIP-S12-03`: the knowledge base's top row -- the group «Эксперт» with the cards «Отклонено», «Принято», «Не решено» (only
 * while there is such a decision) and «Все», «Фильтры ▾» and «Память решений» on the right -- with the server's counts.
 *
 * Each card's number is the `total` of `listDecisions` for its verdict, read with `limit=1`, under the same project and
 * category the list is read under. The tests hold what a plausible wrong version would break: a number taken from the
 * length of the page on screen, a number that follows the verdict the card itself sets, a zero drawn for a read that
 * failed, a card that keeps a cursor of the page before it, a screen that opens on «Все» and not on «Отклонено», a «Не решено»
 * card that stays at zero, and a list of verdicts beside the cards that says the same thing twice.
 *
 * Mounted live (`analysis-settings/live-render.ts`) because a press and a select change are events the one-pass render
 * cannot deliver. Only the transport is replaced.
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
import { listDecisions, listProjects } from '@/shared/api';
import type { ApiResponse, DecisionRecord, DecisionRecordPage } from '@/shared/api';
import { JOURNAL_PAGE_LIMIT } from '@/entities/expert-decision';
import { KnowledgeBase } from '@/widgets/knowledge-base';

import { mountLive } from '../analysis-settings/live-render';
import { RoutedAddress } from './routed-address';
import type { LiveRender } from '../analysis-settings/live-render';
import '../review/fixtures';

const ULID = '01M2545JSD15ETSNNV904X991F';
const A = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';

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
    project_uid: A,
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

const PAGE_1 = [record(1), record(2)];

function answer(items: DecisionRecord[], next: string | null, total: number): ApiResponse<DecisionRecordPage> {
  return { data: { items, page: { next_cursor: next }, total }, status: 200, correlationId: 'cid-chips' };
}

type Query = { category?: string; verdict?: string; cursor?: string; limit?: number; project_uid?: string };

/** What the server says «Не решено» holds; a test that wants the card gone sets it to zero. */
let undecided = 40;

/** What the server says each verdict holds, by the filters a read carries: not one of them is the length of a page. */
function totalOf(query: Query): number {
  const base = { accepted: 12, rejected: 5, pending: undecided, all: 57 };
  const narrowed = { accepted: 2, rejected: 1, pending: 3, all: 6 };
  const projectOnly = { accepted: 7, rejected: 0, pending: 9, all: 16 };
  const figures = query.category !== undefined ? narrowed : query.project_uid !== undefined ? projectOnly : base;
  return figures[(query.verdict ?? 'all') as keyof typeof figures];
}

const journal = vi.mocked(listDecisions);
const projects = vi.mocked(listProjects);
const everyQuery = (): Query[] => journal.mock.calls.map((call) => (call[0] as { query: Query }).query);
/** The chips' reads: one record per page, the whole journal in `total`. */
const countQueries = (): Query[] => everyQuery().filter((query) => query.limit === 1);
/** The list's own pages. */
const listQueries = (): Query[] => everyQuery().filter((query) => query.limit !== 1);

beforeEach(() => {
  undecided = 40;
  journal.mockReset();
  journal.mockImplementation((async (input: { query: Query }) => {
    const query = input.query;
    if (query.limit === 1) return answer([PAGE_1[0] as DecisionRecord], null, totalOf(query));
    return answer(PAGE_1, query.cursor === undefined ? 'cursor-1' : null, totalOf(query));
  }) as unknown as typeof listDecisions);
  projects.mockReset();
  projects.mockImplementation((async () => ({
    data: { items: [], page: { next_cursor: null } },
    status: 200,
    correlationId: 'cid-projects',
  })) as unknown as typeof listProjects);
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

async function press(view: LiveRender, label: string): Promise<boolean> {
  const delivered = await view.press(label);
  await settled(view);
  return delivered;
}

async function change(view: LiveRender, label: string, value: string): Promise<boolean> {
  const delivered = await view.change(label, value);
  await settled(view);
  return delivered;
}

/** The text a browser would show: tags stripped. */
function visible(markup: string): string {
  return markup.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
}

/** The opening tag of the chip for one verdict. */
function chipTag(markup: string, choice: string): string {
  const found = markup.match(new RegExp(`<button[^>]*data-kb-verdict="${choice}"[^>]*>`));
  if (found === null) throw new Error(`no chip for ${choice}`);
  return found[0];
}

describe('the cards carry the server’s counts', () => {
  let live: LiveRender | null = null;
  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  async function mountAt(query = ''): Promise<LiveRender> {
    live = await mountLive(page(freshClient(), query));
    await settled(live);
    return live;
  }

  it('reads each verdict’s total with one record per page, and the whole journal for «Все»', async () => {
    await mountAt();
    expect(countQueries()).toHaveLength(4);
    expect(countQueries()).toEqual(
      expect.arrayContaining([
        { verdict: 'accepted', limit: 1 },
        { verdict: 'rejected', limit: 1 },
        { verdict: 'pending', limit: 1 },
        { limit: 1 },
      ]),
    );
    // The screen opens on «Отклонено»: the first page of the rejected decisions, no cursor.
    expect(listQueries()).toEqual([{ verdict: 'rejected', limit: JOURNAL_PAGE_LIMIT }]);
  });

  it('draws the cards in the original’s order, under the caption «Эксперт», with the server’s numbers, not the length of the page on screen', async () => {
    const view = await mountAt();
    expect(PAGE_1).toHaveLength(2);
    expect(view.count('Принято 12')).toBe(1);
    expect(view.count('Отклонено 5')).toBe(1);
    expect(view.count('Не решено 40')).toBe(1);
    expect(view.count('Все 57')).toBe(1);
    const text = visible(view.markup());
    expect(text.indexOf('Эксперт')).toBeLessThan(text.indexOf('Отклонено 5'));
    expect(text.indexOf('Отклонено 5')).toBeLessThan(text.indexOf('Принято 12'));
    expect(text.indexOf('Принято 12')).toBeLessThan(text.indexOf('Не решено 40'));
    expect(text.indexOf('Не решено 40')).toBeLessThan(text.indexOf('Все 57'));
    expect(chipTag(view.markup(), 'rejected')).toContain('data-kb-verdict-total="5"');
    expect(view.markup()).toMatch(/role="group" aria-label="Эксперт"/);
  });

  it('gives each number the tone its verdict has everywhere: red for «Отклонено», green for «Принято», grey for the rest', async () => {
    const markup = (await mountAt()).markup();
    const pill = (choice: string) => new RegExp(`data-kb-verdict="${choice}"[^>]*>[^<]*<span class="am-badge am-badge--(\\w+)`).exec(markup)?.[1];
    expect([pill('rejected'), pill('accepted'), pill('pending'), pill('all')]).toEqual(['failed', 'ok', 'pending', 'inert']);
  });

  it('starts on «Отклонено», the original’s first card, and «Все» is a card that has to be chosen', async () => {
    const view = await mountAt();
    expect(chipTag(view.markup(), 'rejected')).toContain('aria-pressed="true"');
    expect(chipTag(view.markup(), 'all')).toContain('aria-pressed="false"');
    expect(chipTag(view.markup(), 'accepted')).toContain('aria-pressed="false"');
  });

  it('draws «Не решено» only while the journal holds such a decision', async () => {
    undecided = 0;
    const view = await mountAt();
    expect(view.count('Не решено 0')).toBe(0);
    expect(view.markup()).not.toContain('data-kb-verdict="pending"');
    // The three others are there, with the zero it answered for the one that is not.
    expect(view.count('Отклонено 5')).toBe(1);
    expect(view.count('Принято 12')).toBe(1);
    expect(view.count('Все 57')).toBe(1);
  });

  it('keeps «Не решено» on screen when it is the card that is chosen, even at zero, so the list never says a filter that is not drawn', async () => {
    undecided = 0;
    const view = await mountAt('verdict=pending');
    expect(view.count('Не решено 0')).toBe(1);
    expect(chipTag(view.markup(), 'pending')).toContain('aria-pressed="true"');
  });

  it('draws «Не решено» for a count the server has not answered for it: no card is shown on a number nobody read', async () => {
    journal.mockImplementation((async (input: { query: Query }) => {
      const query = input.query;
      if (query.limit === 1 && query.verdict === 'pending') throw new Error('the count read failed');
      if (query.limit === 1) return answer([PAGE_1[0] as DecisionRecord], null, totalOf(query));
      return answer(PAGE_1, null, totalOf(query));
    }) as unknown as typeof listDecisions);
    const view = await mountAt();
    expect(view.markup()).not.toContain('data-kb-verdict="pending"');
  });

  it('keeps a zero the server answered as a zero', async () => {
    const view = await mountAt(`project=${A}`);
    expect(view.count('Отклонено 0')).toBe(1);
    expect(chipTag(view.markup(), 'rejected')).toContain('data-kb-verdict-total="0"');
  });

  it('sends the project of the address with every count', async () => {
    const view = await mountAt(`project=${A}`);
    expect(countQueries()).toEqual(
      expect.arrayContaining([
        { project_uid: A, verdict: 'accepted', limit: 1 },
        { project_uid: A, limit: 1 },
      ]),
    );
    expect(countQueries().every((query) => query.project_uid === A)).toBe(true);
    expect(view.count('Принято 7')).toBe(1);
    expect(view.count('Все 16')).toBe(1);
  });

  it('follows the category: a new category is four new counts', async () => {
    const view = await mountAt();
    journal.mockClear();
    expect(await change(view, 'Категория', 'dimensions')).toBe(true);
    expect(countQueries()).toHaveLength(4);
    expect(countQueries().every((query) => query.category === 'dimensions')).toBe(true);
    expect(view.count('Принято 2')).toBe(1);
    expect(view.count('Все 6')).toBe(1);
  });

  it('draws no number, and no zero, for a count the server did not give', async () => {
    journal.mockImplementation((async (input: { query: Query }) => {
      const query = input.query;
      if (query.limit === 1 && query.verdict === 'rejected') throw new Error('the count read failed');
      if (query.limit === 1) return answer([PAGE_1[0] as DecisionRecord], null, totalOf(query));
      return answer(PAGE_1, null, totalOf(query));
    }) as unknown as typeof listDecisions);
    const view = await mountAt();
    expect(view.count('Отклонено —')).toBe(1);
    expect(chipTag(view.markup(), 'rejected')).not.toContain('data-kb-verdict-total');
    expect(view.count('Принято 12')).toBe(1);
  });
});

describe('a card sets the verdict filter', () => {
  let live: LiveRender | null = null;
  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  async function mountAt(query = ''): Promise<LiveRender> {
    live = await mountLive(page(freshClient(), query));
    await settled(live);
    return live;
  }

  it('asks the list for that verdict, from the first page, and marks the chip pressed', async () => {
    const view = await mountAt();
    journal.mockClear();
    expect(await press(view, 'Принято 12')).toBe(true);
    expect(listQueries()).toEqual([{ verdict: 'accepted', limit: JOURNAL_PAGE_LIMIT }]);
    expect(chipTag(view.markup(), 'accepted')).toContain('aria-pressed="true"');
    expect(chipTag(view.markup(), 'rejected')).toContain('aria-pressed="false"');
  });

  it('does not recount: a card’s number is its own verdict’s, whatever verdict is chosen', async () => {
    const view = await mountAt();
    journal.mockClear();
    await press(view, 'Не решено 40');
    expect(countQueries()).toEqual([]);
    expect(view.count('Принято 12')).toBe(1);
    expect(view.count('Все 57')).toBe(1);
  });

  it('has no list of verdicts beside the cards: they say the same thing, so the screen says it once', async () => {
    const view = await mountAt();
    expect(view.markup()).not.toContain('kb-filter-verdict');
    expect(view.markup()).not.toContain('Любой вердикт');
    expect(visible(view.markup())).not.toContain('Вердикт');
    await expect(view.change('Вердикт', 'rejected')).rejects.toThrow(/expected one label/);
  });

  it('returns to the first page, because a cursor belongs to the filter it was issued under', async () => {
    const view = await mountAt();
    expect(await press(view, 'Далее')).toBe(true);
    expect(listQueries().at(-1)).toEqual({ verdict: 'rejected', limit: JOURNAL_PAGE_LIMIT, cursor: 'cursor-1' });
    journal.mockClear();
    await press(view, 'Принято 12');
    expect(listQueries()).toEqual([{ verdict: 'accepted', limit: JOURNAL_PAGE_LIMIT }]);
    expect(listQueries().every((query) => query.cursor === undefined)).toBe(true);
  });

  it('«Все» takes the verdict off, and is the one card that asks for no verdict', async () => {
    const view = await mountAt();
    journal.mockClear();
    await press(view, 'Все 57');
    expect(listQueries()).toEqual([{ limit: JOURNAL_PAGE_LIMIT }]);
    expect(chipTag(view.markup(), 'all')).toContain('aria-pressed="true"');
    expect(chipTag(view.markup(), 'rejected')).toContain('aria-pressed="false"');
    expect(visible(view.markup())).toContain('Решение номер 1');
    // Back on «Отклонено», and the cards’ own numbers were never asked again.
    journal.mockClear();
    await press(view, 'Отклонено 5');
    expect(countQueries()).toEqual([]);
    expect(chipTag(view.markup(), 'rejected')).toContain('aria-pressed="true"');
  });
});

describe('the top row (UIP-S12-03)', () => {
  let live: LiveRender | null = null;
  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  async function mountAt(query = ''): Promise<LiveRender> {
    live = await mountLive(page(freshClient(), query));
    await settled(live);
    return live;
  }

  it('keeps the type, the view and the category inside «Фильтры ▾», the browser’s own disclosure, and nothing else', async () => {
    const markup = (await mountAt()).markup();
    const menu = /<details[^>]*data-kb-filter-menu[^>]*>([\s\S]*?)<\/details>/.exec(markup)?.[1] ?? '';
    expect(menu).toMatch(/^<summary[^>]*>Фильтры ▾<\/summary>/);
    for (const word of ['Тип', 'Вид', 'Категория']) expect(visible(menu)).toContain(word);
    for (const choice of ['all', 'findings', 'proposals']) expect(menu).toContain(`data-kb-kind="${choice}"`);
    expect(menu).not.toContain('data-kb-kind="memory"');
    expect(menu).not.toContain('data-kb-verdict');
    // Closed until it is opened: the handle says nothing is narrowed, and the cards are outside it.
    expect(markup).not.toMatch(/<details[^>]*\sopen/);
    expect(markup).not.toContain('data-kb-filter-count');
  });

  it('says how many of the filters inside are not at their first-screen value, on the handle', async () => {
    const view = await mountAt('category=dimensions&view=events');
    expect(view.markup()).toMatch(/<summary[^>]*>Фильтры ▾<span[^>]*data-kb-filter-count="2"[^>]*>2<\/span><\/summary>/);
  });

  it('keeps the cards on the left and the handle on the right, in one row', async () => {
    const view = await mountAt();
    const row = /<div[^>]*data-kb-top-row[^>]*>([\s\S]*?)<div class="[^"]*actions[^"]*">([\s\S]*)/.exec(view.markup());
    expect(row).not.toBeNull();
    expect(row?.[1]).toContain('data-kb-group="expert"');
    expect(row?.[1]).not.toContain('data-kb-filter-menu');
    expect(row?.[2]).toContain('data-kb-filter-menu');
    expect(row?.[2]).not.toContain('data-kb-group');
  });

  it('draws the cards for «Замечания» only, and the handle and the memory button on every type', async () => {
    const view = await mountAt();
    for (const label of ['Предложения', 'Все']) {
      await press(view, label);
      expect(view.markup()).not.toContain('data-kb-group');
      expect(view.markup()).toContain('data-kb-filter-menu');
    }
  });
});

describe('the cards belong to «Замечания» only', () => {
  it('draws no card and reads no count for the proposals half', async () => {
    const live = await mountLive(page(freshClient(), ''));
    try {
      await settled(live);
      journal.mockClear();
      await press(live, 'Предложения');
      expect(live.markup()).not.toContain('data-kb-group');
      expect(live.markup()).not.toContain('data-kb-verdict');
      expect(countQueries()).toEqual([]);
    } finally {
      await live.unmount();
    }
  });
});
