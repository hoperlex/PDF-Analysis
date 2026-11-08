/**
 * `UI-PARITY-COMPLETENESS-01`: the knowledge base is PAGED, and says so.
 *
 * `listDecisions` answers 50 decisions and a `next_cursor`. The screen read the first page and had
 * no «Далее», so every decision after the fiftieth was unreachable from it. «Далее» and «Назад»
 * now walk the server's opaque cursors with a stack -- the construction the execution journal
 * already uses -- and a cursor belongs to the filter it was issued under, so changing either
 * filter returns to the first page.
 *
 * Mounted in a minimal DOM (`analysis-settings/live-render.ts`): a button press and a select change
 * are events the one-pass render of `harness.ts` cannot deliver. Only the transport is replaced.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, listDecisions: vi.fn() };
});

import { KnowledgeBaseEagerSeam, KnowledgeBasePage } from '@/_pages/knowledge-base';
import { listDecisions } from '@/shared/api';
import type { ApiResponse, DecisionRecord, DecisionRecordPage } from '@/shared/api';
import { JOURNAL_PAGE_LIMIT } from '@/entities/expert-decision';
import { KnowledgeBase } from '@/widgets/knowledge-base';

import { mountLive } from '../analysis-settings/live-render';
import { RoutedAddress } from './routed-address';
import type { LiveRender } from '../analysis-settings/live-render';
import '../review/fixtures';

const ULID = '01M2545JSD15ETSNNV904X991F';

function record(n: number, over: Partial<DecisionRecord> = {}): DecisionRecord {
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
    project_name: 'Школа',
    document_name: 'АР-1',
    category: 'internal_contradiction',
    finding_text: `Решение номер ${n}`,
    current_verdict: 'accepted',
    decision_event_count: 1,
    ...over,
  };
}

const PAGE_1 = [record(1), record(2)];
const PAGE_2 = [record(3), record(4)];
const PAGE_3 = [record(5)];
const FILTERED = [record(9, { category: 'dimensions', finding_text: 'Решение отобранное по категории' })];
const ACCEPTED = [record(8, { finding_text: 'Решение отобранное по вердикту' })];

function answer(items: DecisionRecord[], next: string | null): ApiResponse<DecisionRecordPage> {
  return { data: { items, page: { next_cursor: next }, total: items.length }, status: 200, correlationId: 'cid-kb' };
}

/** The first render starts the query in an effect; it settles on zero-delay timers after it. */
async function settled(view: LiveRender): Promise<void> {
  for (let round = 0; round < 5; round += 1) {
    await view.settle(() => new Promise<void>((done) => setTimeout(done, 0)));
  }
}

/** A press, then the ticks the page it asks for needs to arrive. */
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

type Query = { category?: string; verdict?: string; cursor?: string; limit?: number };

const journal = vi.mocked(listDecisions);
const everyQuery = (): Query[] => journal.mock.calls.map((call) => (call[0] as { query: Query }).query);
/**
 * The journal's own pages. The verdict chips (`UI-B-32`) read `total` with `limit=1` beside them; those four reads are
 * asserted in `knowledge-base-verdict-chips.test.ts`, and are left out here so these tests keep naming the list's reads.
 */
const queries = (): Query[] => everyQuery().filter((query) => query.limit !== 1);

beforeEach(() => {
  journal.mockReset();
  journal.mockImplementation((async (input: { query: Query }) => {
    const { category, verdict, cursor } = input.query;
    if (category === 'dimensions') return answer(FILTERED, null);
    if (verdict === 'accepted') return answer(ACCEPTED, null);
    if (cursor === undefined) return answer(PAGE_1, 'cursor-1');
    if (cursor === 'cursor-1') return answer(PAGE_2, 'cursor-2');
    if (cursor === 'cursor-2') return answer(PAGE_3, null);
    throw new Error(`an unexpected cursor ${cursor}`);
  }) as unknown as typeof listDecisions);
});

describe('«Далее» and «Назад» walk the journal by cursor', () => {
  let live: LiveRender | null = null;

  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  async function mount(): Promise<LiveRender> {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false, refetchOnMount: false, gcTime: Infinity, staleTime: 30_000 } },
    });
    live = await mountLive(
      createElement(
        QueryClientProvider,
        { client },
        createElement(
          KnowledgeBaseEagerSeam.Provider,
          { value: KnowledgeBase },
          createElement(RoutedAddress, { query: '' }, createElement(KnowledgeBasePage)),
        ),
      ),
    );
    await settled(live);
    return live;
  }

  it('opens on the first page, with «Далее» and without a way back', async () => {
    const view = await mount();
    const markup = view.markup();

    expect(markup).toContain('Решение номер 1<');
    expect(markup).toContain('Решение номер 2<');
    expect(markup).not.toContain('Решение номер 3<');
    expect(queries()).toEqual([{ limit: JOURNAL_PAGE_LIMIT }]);
    expect(await press(view, 'Назад')).toBe(false);
  });

  it('goes forward with the cursor the server gave, page by page, until there is none', async () => {
    const view = await mount();

    expect(await press(view, 'Далее')).toBe(true);
    expect(view.markup()).toContain('Решение номер 3<');
    expect(view.markup()).not.toContain('Решение номер 1<');

    expect(await press(view, 'Далее')).toBe(true);
    expect(view.markup()).toContain('Решение номер 5<');

    // The last page names no cursor: «Далее» is there, and it is disabled.
    expect(await press(view, 'Далее')).toBe(false);
    expect(queries()).toEqual([
      { limit: JOURNAL_PAGE_LIMIT },
      { limit: JOURNAL_PAGE_LIMIT, cursor: 'cursor-1' },
      { limit: JOURNAL_PAGE_LIMIT, cursor: 'cursor-2' },
    ]);
  });

  it('goes back one page at a time, to the first page and no further', async () => {
    const view = await mount();
    await press(view, 'Далее');
    await press(view, 'Далее');
    expect(view.markup()).toContain('Решение номер 5<');

    expect(await press(view, 'Назад')).toBe(true);
    expect(view.markup()).toContain('Решение номер 3<');
    expect(view.markup()).not.toContain('Решение номер 5<');

    expect(await press(view, 'Назад')).toBe(true);
    expect(view.markup()).toContain('Решение номер 1<');
    expect(await press(view, 'Назад')).toBe(false);
    // A page already read is not read again (the application's own 30 s freshness).
    expect(queries()).toHaveLength(3);
  });

  it('shows no pager when the whole journal fits one page', async () => {
    journal.mockImplementation((async () => answer(PAGE_1, null)) as unknown as typeof listDecisions);
    const view = await mount();
    expect(view.markup()).toContain('Решение номер 2<');
    expect(view.count('Далее')).toBe(0);
    expect(view.count('Назад')).toBe(0);
  });
});

describe('a filter change returns to the first page', () => {
  let live: LiveRender | null = null;

  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  async function onSecondPage(): Promise<LiveRender> {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false, refetchOnMount: false, gcTime: Infinity, staleTime: 30_000 } },
    });
    live = await mountLive(
      createElement(
        QueryClientProvider,
        { client },
        createElement(
          KnowledgeBaseEagerSeam.Provider,
          { value: KnowledgeBase },
          createElement(RoutedAddress, { query: '' }, createElement(KnowledgeBasePage)),
        ),
      ),
    );
    await settled(live);
    await press(live, 'Далее');
    expect(live.markup()).toContain('Решение номер 3<');
    journal.mockClear();
    return live;
  }

  it('asks for the new category with NO cursor, and has nowhere to go back to', async () => {
    const view = await onSecondPage();

    expect(await change(view, 'Категория', 'dimensions')).toBe(true);

    expect(queries()).toEqual([{ category: 'dimensions', limit: JOURNAL_PAGE_LIMIT }]);
    expect(view.markup()).toContain('Решение отобранное по категории');
    expect(view.count('Назад')).toBe(0);
  });

  it('asks for the new verdict with NO cursor', async () => {
    const view = await onSecondPage();

    expect(await change(view, 'Вердикт', 'accepted')).toBe(true);

    expect(queries()).toEqual([{ verdict: 'accepted', limit: JOURNAL_PAGE_LIMIT }]);
    expect(view.markup()).toContain('Решение отобранное по вердикту');
  });

  it('does not bring the old cursor back when the filter is cleared', async () => {
    const view = await onSecondPage();
    await change(view, 'Вердикт', 'accepted');
    journal.mockClear();

    await change(view, 'Вердикт', 'all');

    // The first page of the unfiltered journal, not page 2 and not a read from the old cursor.
    expect(view.markup()).toContain('Решение номер 1<');
    expect(view.markup()).not.toContain('Решение номер 3<');
    expect(queries().every((query) => query.cursor === undefined)).toBe(true);
    expect(await press(view, 'Назад')).toBe(false);
  });
});
