/**
 * «Автообновление» of the journal, against a real React Query timer (`UI-B-43`).
 *
 * React Query schedules no refetch interval on a server, and this suite runs in node, so every other test of the
 * polling policy can only ask the policy function. This one tells React Query it is not on a server
 * (`environmentManager.setIsServer`, restored after), drives an observer with fake timers and counts reads: on, the
 * journal is read again every interval; off, it is not read at all; on again, it is back.
 */

import { QueryClient, QueryObserver, environmentManager } from '@tanstack/react-query';
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest';

import { journalQueryOptions } from '@/entities/execution';

const RUN_ID = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const NO_NEXT = { next_cursor: null } as const;

const wasServer = environmentManager.isServer();
beforeAll(() => environmentManager.setIsServer(() => false));
afterAll(() => environmentManager.setIsServer(() => wasServer));

describe('«Автообновление» drives the real timer', () => {
  it('reads again every 10 s while on, not at all while off, and again once on', async () => {
    vi.useFakeTimers();
    try {
      const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } });
      let reads = 0;
      const optionsFor = (autoRefresh: boolean) => ({
        ...journalQueryOptions(RUN_ID, undefined, true, autoRefresh),
        queryFn: async () => {
          reads += 1;
          return { items: [], page: NO_NEXT };
        },
      });
      const observer = new QueryObserver(client, optionsFor(true));
      const unsubscribe = observer.subscribe(() => {});
      await vi.advanceTimersByTimeAsync(0);
      expect(reads).toBe(1);
      await vi.advanceTimersByTimeAsync(10_000);
      expect(reads, 'a timed read while on').toBe(2);
      await vi.advanceTimersByTimeAsync(10_000);
      expect(reads).toBe(3);

      observer.setOptions(optionsFor(false));
      await vi.advanceTimersByTimeAsync(120_000);
      expect(reads, 'no timed read while off').toBe(3);

      observer.setOptions(optionsFor(true));
      await vi.advanceTimersByTimeAsync(10_000);
      expect(reads, 'the timed read is back').toBe(4);
      unsubscribe();
    } finally {
      vi.useRealTimers();
    }
  });
});
