/**
 * `UI-PARITY-COMPLETENESS-01`: «Разбор находок» shows EVERY finding of the run, or says it could
 * not -- never the first page as if it were the whole.
 *
 * `listRunFindings` pages (50 by default, 200 at most). The review screen asked for one page and
 * showed a run with 107 findings as a run with 50, while the CSV and XLSX exports carried all 107.
 * What is pinned here:
 *
 *   - the reader asks for 200 per page, follows `next_cursor` until it is `null`, and passes the
 *     abort signal to every request;
 *   - the 50 + 50 + 7 run is reachable in full on the real screen, mounted in a minimal DOM;
 *   - a failure on page 2 gives the error state with a retry and NO list, not the 50 already read;
 *   - the server contradicting its own paging (a repeated cursor, a finding on two pages, a list
 *     that never ends) is a fault, never a short list;
 *   - one `queryFn` fills the key: no other site names `queryKeys.runs.findings(` as a `queryKey`.
 *
 * Only the transport is replaced: the generated operations the tree calls.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, listRunFindings: vi.fn() };
});

import { ReviewPage } from '@/_pages/review';
import { ApiError, listRunFindings, queryKeys } from '@/shared/api';
import type { ApiResponse, ErrorCode, Finding, FindingPage } from '@/shared/api';
import {
  RUN_FINDINGS_MAX_PAGES,
  RUN_FINDINGS_PAGE_LIMIT,
  RunFindingsReadFault,
  readAllRunFindings,
  runFindingsQueryOptions,
} from '@/entities/finding';

import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { PROJECT_UID, RUN_ID, finding, observation, runStatus } from './fixtures';
import { RoutedReviewAddress, resetRoutedAddress } from './routed-review-address';

const list = vi.mocked(listRunFindings);

/**
 * `mountLive` flushes the first render; the queries start in that render's effects and settle on
 * zero-delay timers after it. Give them those ticks, so a test reads the screen after the reads.
 */
async function settled(view: LiveRender): Promise<void> {
  for (let round = 0; round < 5; round += 1) {
    await view.settle(() => new Promise<void>((done) => setTimeout(done, 0)));
  }
}

/** A finding with its own identity and its own words, so the screen can be asked for it by name. */
function numbered(n: number): Finding {
  const tail = String(n).padStart(4, '0');
  return finding({
    finding_uid: `fnd_01J9ZQ8K7NHVXW3T2R5M6P${tail}`,
    observation: observation({
      finding_observation_id: `fobs_01J9ZQ8K7NHVXW3T2R5M6P${tail}`,
      finding_text: `Находка номер ${n}`,
    }),
  });
}

const ALL = Array.from({ length: 107 }, (_, index) => numbered(index + 1));

function answer(items: Finding[], nextCursor: string | null): ApiResponse<FindingPage> {
  return { data: { items, page: { next_cursor: nextCursor } }, status: 200, correlationId: 'cid-page' };
}

/** The three pages of a 107-finding run: 50, 50 and 7, joined by `cursor-1` and `cursor-2`. */
function threePages(): void {
  list.mockImplementation((async (input: { query?: { cursor?: string } }) => {
    const cursor = input.query?.cursor;
    if (cursor === undefined) return answer(ALL.slice(0, 50), 'cursor-1');
    if (cursor === 'cursor-1') return answer(ALL.slice(50, 100), 'cursor-2');
    if (cursor === 'cursor-2') return answer(ALL.slice(100), null);
    throw new Error(`an unexpected cursor ${cursor}`);
  }) as unknown as typeof listRunFindings);
}

function serverError(): ApiError {
  return new ApiError(
    503,
    {
      contract_version: '1.45.0',
      error_code: 'dependency_unavailable' as ErrorCode,
      message: 'A caller-safe sentence.',
      correlation_id: 'cid-page-2',
      retryable: true,
      details: { dependency: 'metadata_store' },
    },
    'cid-page-2',
  );
}

type Query = { cursor?: string; limit?: number } | undefined;
const queryOf = (call: unknown[]): Query => (call[0] as { query?: Query }).query;
const optionsOf = (call: unknown[]): { signal?: AbortSignal } => call[1] as { signal?: AbortSignal };

beforeEach(() => {
  list.mockReset();
});

describe('the reader asks for the whole list', () => {
  it('requests 200 per page, follows next_cursor to its end and returns all 107 in order', async () => {
    threePages();
    const result = await readAllRunFindings(RUN_ID, new AbortController().signal);

    expect(result.data.items.map((item) => item.observation.finding_text)).toEqual(
      ALL.map((item) => item.observation.finding_text),
    );
    expect(result.data.page.next_cursor).toBeNull();
    expect(list.mock.calls.map(queryOf)).toEqual([
      { limit: 200 },
      { limit: 200, cursor: 'cursor-1' },
      { limit: 200, cursor: 'cursor-2' },
    ]);
    expect(RUN_FINDINGS_PAGE_LIMIT).toBe(200);
  });

  it('asks once for a run that fits one page', async () => {
    list.mockResolvedValue(answer(ALL.slice(0, 3), null));
    const result = await readAllRunFindings(RUN_ID, new AbortController().signal);
    expect(result.data.items).toHaveLength(3);
    expect(list).toHaveBeenCalledTimes(1);
  });

  it('passes the abort signal to every request', async () => {
    threePages();
    const controller = new AbortController();
    await readAllRunFindings(RUN_ID, controller.signal);
    expect(list).toHaveBeenCalledTimes(3);
    for (const call of list.mock.calls) expect(optionsOf(call).signal).toBe(controller.signal);
  });

  it('stops at an abort between pages and asks for no further page', async () => {
    const controller = new AbortController();
    list.mockImplementation((async (input: { query?: { cursor?: string } }) => {
      if (input.query?.cursor === undefined) {
        // The reviewer leaves the screen while the first page is in flight.
        controller.abort();
        return answer(ALL.slice(0, 50), 'cursor-1');
      }
      return answer(ALL.slice(50), null);
    }) as unknown as typeof listRunFindings);

    const failure = await readAllRunFindings(RUN_ID, controller.signal).catch((e: unknown) => e);
    expect((failure as Error).name).toBe('AbortError');
    expect(list).toHaveBeenCalledTimes(1);
  });

  it('aborts through the query: the signal React Query hands the queryFn reaches the request', async () => {
    threePages();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const pending = client.fetchQuery(runFindingsQueryOptions(RUN_ID));
    await pending;
    for (const call of list.mock.calls) expect(optionsOf(call).signal).toBeInstanceOf(AbortSignal);
    expect(client.getQueryData(queryKeys.runs.findings(RUN_ID))).toMatchObject({
      data: { page: { next_cursor: null } },
    });
  });
});

describe('a list that cannot be called complete is an error, with nothing cached as a list', () => {
  it('fails with the error of page 2 and keeps none of the 50 already read', async () => {
    list.mockImplementation((async (input: { query?: { cursor?: string } }) => {
      if (input.query?.cursor === undefined) return answer(ALL.slice(0, 50), 'cursor-1');
      throw serverError();
    }) as unknown as typeof listRunFindings);

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    await expect(client.fetchQuery(runFindingsQueryOptions(RUN_ID))).rejects.toBeInstanceOf(ApiError);
    expect(client.getQueryData(queryKeys.runs.findings(RUN_ID))).toBeUndefined();
  });

  it('refuses a cursor it was already given', async () => {
    list.mockImplementation((async (input: { query?: { cursor?: string } }) =>
      input.query?.cursor === undefined
        ? answer(ALL.slice(0, 2), 'cursor-1')
        : answer(ALL.slice(2, 4), 'cursor-1')) as unknown as typeof listRunFindings);
    const failure = await readAllRunFindings(RUN_ID, new AbortController().signal).catch((e: unknown) => e);
    expect(failure).toBeInstanceOf(RunFindingsReadFault);
    expect((failure as Error).message).toContain('повторил курсор');
    expect(list).toHaveBeenCalledTimes(2);
  });

  it('refuses a finding that arrives on two pages', async () => {
    list.mockImplementation((async (input: { query?: { cursor?: string } }) =>
      input.query?.cursor === undefined
        ? answer(ALL.slice(0, 3), 'cursor-1')
        : answer(ALL.slice(2, 5), null)) as unknown as typeof listRunFindings);
    const failure = await readAllRunFindings(RUN_ID, new AbortController().signal).catch((e: unknown) => e);
    expect(failure).toBeInstanceOf(RunFindingsReadFault);
    expect((failure as Error).message).toContain('на двух страницах');
  });

  it('refuses a list that never ends, after the page bound and not before', async () => {
    let served = 0;
    list.mockImplementation((async () => {
      served += 1;
      return answer([numbered(served)], `cursor-${served}`);
    }) as unknown as typeof listRunFindings);
    const failure = await readAllRunFindings(RUN_ID, new AbortController().signal).catch((e: unknown) => e);
    expect(failure).toBeInstanceOf(RunFindingsReadFault);
    expect(list).toHaveBeenCalledTimes(RUN_FINDINGS_MAX_PAGES);
  });
});

describe('the review screen shows the complete list, or the error, and never a partial list', () => {
  let live: LiveRender | null = null;

  afterEach(async () => {
    await live?.unmount();
    live = null;
    resetRoutedAddress();
  });

  async function mount(): Promise<LiveRender> {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false, refetchOnMount: false, gcTime: Infinity } },
    });
    client.setQueryData(queryKeys.runs.detail(RUN_ID), runStatus({ published_finding_count: 107 }));
    // The extended-analysis summary reads this key; an empty answer draws nothing.
    client.setQueryData(['extended-run-review', RUN_ID], {});
    live = await mountLive(
      createElement(
        QueryClientProvider,
        { client },
        // `D-401`: the page opens the first finding that waits and writes it to the address when the list arrives, so the window it
        // is mounted in needs an address to write to.
        createElement(
          RoutedReviewAddress,
          { pathname: `/projects/${PROJECT_UID}/runs/${RUN_ID}/review`, query: '' },
          createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID }),
        ),
      ),
    );
    await settled(live);
    return live;
  }

  const rows = (markup: string): number => markup.split('data-finding-uid=').length - 1;

  it('lists all 107 findings of a 50 + 50 + 7 run', async () => {
    threePages();
    const view = await mount();
    const markup = view.markup();

    expect(markup).toContain('data-finding-count="107"');
    expect(rows(markup)).toBe(107);
    for (const edge of [1, 50, 51, 100, 101, 107]) expect(markup).toContain(`Находка номер ${edge}<`);
    expect(markup).not.toContain('Не удалось загрузить находки');
    expect(list).toHaveBeenCalledTimes(3);
  });

  it('gives the error state, with a retry and no list, when page 2 fails', async () => {
    list.mockImplementation((async (input: { query?: { cursor?: string } }) => {
      if (input.query?.cursor === undefined) return answer(ALL.slice(0, 50), 'cursor-1');
      throw serverError();
    }) as unknown as typeof listRunFindings);
    const view = await mount();
    const markup = view.markup();

    expect(markup).toContain('Не удалось загрузить находки');
    expect(markup).toContain('cid-page-2');
    expect(view.count('Повторить')).toBe(1);
    // The 50 findings of page 1 were read, and none of them is on the screen.
    expect(rows(markup)).toBe(0);
    expect(markup).not.toContain('Находка номер 1<');
    expect(markup).not.toContain('data-finding-count');
  });

  it('recovers on a retry: the whole list is read again, from the first page', async () => {
    let failing = true;
    list.mockImplementation((async (input: { query?: { cursor?: string } }) => {
      const cursor = input.query?.cursor;
      if (cursor === undefined) return answer(ALL.slice(0, 50), 'cursor-1');
      if (cursor === 'cursor-1') {
        if (failing) throw serverError();
        return answer(ALL.slice(50, 100), 'cursor-2');
      }
      return answer(ALL.slice(100), null);
    }) as unknown as typeof listRunFindings);
    const view = await mount();
    expect(rows(view.markup())).toBe(0);

    failing = false;
    expect(await view.press('Повторить')).toBe(true);
    expect(view.markup()).toContain('data-finding-count="107"');
    expect(rows(view.markup())).toBe(107);
  });

  it('says why no list is shown when the server repeats a cursor, and offers a retry', async () => {
    list.mockImplementation((async (input: { query?: { cursor?: string } }) =>
      input.query?.cursor === undefined
        ? answer(ALL.slice(0, 50), 'cursor-1')
        : answer(ALL.slice(50, 100), 'cursor-1')) as unknown as typeof listRunFindings);
    const view = await mount();
    const markup = view.markup();

    expect(markup).toContain('Не удалось загрузить находки');
    expect(markup).toContain('Список находок не показан, чтобы не выдать часть за целое.');
    expect(view.count('Повторить')).toBe(1);
    expect(rows(markup)).toBe(0);
  });
});

describe('one queryFn fills queryKeys.runs.findings', () => {
  it('can fail: the scan finds a site that names the key as a queryKey', () => {
    expect(namesKeyAsQueryKey("useQuery({ queryKey: queryKeys.runs.findings(runId), queryFn })")).toBe(true);
    expect(namesKeyAsQueryKey('client.invalidateQueries({ queryKey: queryKeys.runs.findings(id) })')).toBe(true);
    expect(namesKeyAsQueryKey('const options = runFindingsQueryOptions(runId);')).toBe(false);
  });

  it('holds: no source file but the entity names the key as a queryKey, other than to invalidate it', async () => {
    const { readFileSync } = await import('node:fs');
    const { join } = await import('node:path');
    const { WEB_ROOT, walkFiles, repoRelative } = await import('../../guards/lib/repo');
    const offenders: string[] = [];
    for (const file of walkFiles(join(WEB_ROOT, 'src'), (name) => /\.tsx?$/.test(name))) {
      const path = repoRelative(file);
      if (path.includes('/entities/finding/api/')) continue;
      if (path.includes('/shared/api/')) continue;
      const source = readFileSync(file, 'utf8');
      // `queryKey: [...]` fills or reads an entry; `invalidateQueries({ queryKey })` only drops
      // it, and the cache module is the one place that does.
      for (const line of source.split('\n')) {
        if (namesKeyAsQueryKey(line) && !line.includes('invalidateQueries')) offenders.push(`${path}: ${line.trim()}`);
      }
    }
    expect(offenders).toEqual([]);
  });
});

function namesKeyAsQueryKey(text: string): boolean {
  return /queryKey:\s*queryKeys\.runs\.findings\(/.test(text);
}
