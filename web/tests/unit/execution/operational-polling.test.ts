/**
 * The polling policy of the queue and the journal.
 *
 * The schedule is asserted on the pure functions, without timers. The wiring is asserted on
 * real React Query `Query` objects: the settled-read counters are what the policy leans on,
 * and a hand-built fake could agree with a wrong idea of them.
 */

import { QueryClient } from '@tanstack/react-query';
import { describe, expect, it } from 'vitest';

import {
  OPERATIONAL_LIST_POLLING, OPERATIONAL_LIST_STALE_MS, isOperationalListStale, operationalListInterval,
} from '@/shared/config';
import { journalQueryOptions, queueQueryOptions, workersQueryOptions } from '@/entities/execution';
import {
  OPERATIONAL_LIST_POLL, advanceLedger, operationalListRefetchInterval,
} from '@/entities/execution/api/operational-poll';

const RUN_ID = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const SECOND = 1_000;

describe('operationalListInterval: the schedule', () => {
  it('reads every 10 s while the tab is visible and the last read succeeded', () => {
    expect(operationalListInterval({ failures: 0, visible: true })).toBe(10 * SECOND);
    expect(OPERATIONAL_LIST_POLLING.intervalMs).toBe(10 * SECOND);
  });

  it('does not schedule a read while the tab is hidden, whatever the failures', () => {
    for (const failures of [0, 1, 2, 3, 9]) {
      expect(operationalListInterval({ failures, visible: false })).toBe(false);
    }
  });

  it('backs off x2 per consecutive failure up to 60 s: 10, 20, 40, 60, 60', () => {
    const schedule = [0, 1, 2, 3, 4, 5, 20].map((failures) => operationalListInterval({ failures, visible: true }));
    expect(schedule).toEqual([10, 20, 40, 60, 60, 60, 60].map((s) => s * SECOND));
  });

  it('returns to 10 s after a success (the failure streak is zero again)', () => {
    expect(operationalListInterval({ failures: 3, visible: true })).toBe(60 * SECOND);
    expect(operationalListInterval({ failures: 0, visible: true })).toBe(10 * SECOND);
  });

  it('treats a nonsensical failure count as no failures instead of scheduling NaN', () => {
    expect(operationalListInterval({ failures: Number.NaN, visible: true })).toBe(10 * SECOND);
    expect(operationalListInterval({ failures: -4, visible: true })).toBe(10 * SECOND);
    expect(operationalListInterval({ failures: 2.9, visible: true })).toBe(40 * SECOND);
  });
});

describe('isOperationalListStale: when data stops looking current', () => {
  const updated = 1_000_000;

  it('puts the threshold at three intervals', () => {
    expect(OPERATIONAL_LIST_STALE_MS).toBe(3 * OPERATIONAL_LIST_POLLING.intervalMs);
    expect(OPERATIONAL_LIST_STALE_MS).toBe(30 * SECOND);
  });

  it('is fresh up to and including the threshold and stale one millisecond after it', () => {
    expect(isOperationalListStale({ dataUpdatedAt: updated, failed: false, now: updated })).toBe(false);
    expect(isOperationalListStale({ dataUpdatedAt: updated, failed: false, now: updated + 30 * SECOND })).toBe(false);
    expect(isOperationalListStale({ dataUpdatedAt: updated, failed: false, now: updated + 30 * SECOND + 1 })).toBe(true);
  });

  it('is stale after a failed read however recent the last success was', () => {
    expect(isOperationalListStale({ dataUpdatedAt: updated, failed: true, now: updated + SECOND })).toBe(true);
  });

  it('has nothing to call stale before the first successful read', () => {
    expect(isOperationalListStale({ dataUpdatedAt: 0, failed: true, now: updated })).toBe(false);
  });
});

describe('the failure streak, kept from the query counters', () => {
  function client(retry: number | false = false): QueryClient {
    return new QueryClient({ defaultOptions: { queries: { retry, retryDelay: 0, gcTime: Infinity } } });
  }

  /** Run one read of the queue query with the given outcome and ask the policy afterwards. */
  async function read(
    queryClient: QueryClient, outcome: 'ok' | 'fail', asked: number[],
  ): Promise<void> {
    const options = {
      ...queueQueryOptions(),
      queryFn: async () => {
        if (outcome === 'fail') throw new Error('upstream unavailable');
        return { items: [], page: { next_cursor: null }, paused: false };
      },
    };
    const query = queryClient.getQueryCache().build(queryClient, queryClient.defaultQueryOptions(options));
    // React Query asks on every query update, the start of a read included.
    const started = query.fetch(options).catch(() => undefined);
    asked.push(operationalListRefetchInterval(query) as number);
    await started;
    asked.push(operationalListRefetchInterval(query) as number);
  }

  it('walks 10, 20, 40, 60, 60 s over consecutive failed reads and resets on a success', async () => {
    const queryClient = client();
    const afterRead: number[] = [];
    for (const outcome of ['fail', 'fail', 'fail', 'fail', 'fail', 'ok', 'fail'] as const) {
      const asked: number[] = [];
      await read(queryClient, outcome, asked);
      afterRead.push(asked.at(-1) as number);
    }
    expect(afterRead.map((ms) => ms / SECOND)).toEqual([20, 40, 60, 60, 60, 10, 20]);
  });

  it('does not let the start of a read undo the streak (fetchFailureCount restarts there)', async () => {
    const queryClient = client();
    const first: number[] = [];
    await read(queryClient, 'fail', first);
    const second: number[] = [];
    await read(queryClient, 'fail', second);
    // [asked while the read started, asked after it settled]
    expect(second.map((ms) => ms / SECOND)).toEqual([20, 40]);
  });

  it('counts one failed read as one failure even when React Query retried it inside', async () => {
    const queryClient = client(2);
    const asked: number[] = [];
    await read(queryClient, 'fail', asked);
    expect(asked.at(-1)).toBe(20 * SECOND);
  });

  it('asking again about an unchanged query changes nothing', async () => {
    const queryClient = client();
    const asked: number[] = [];
    await read(queryClient, 'fail', asked);
    const query = queryClient.getQueryCache().find({ queryKey: queueQueryOptions().queryKey });
    expect(query).toBeDefined();
    const again = [1, 2, 3].map(() => operationalListRefetchInterval(query!));
    expect(again).toEqual([20 * SECOND, 20 * SECOND, 20 * SECOND]);
  });

  it('advanceLedger: first sight of a failed query counts one failure, of a healthy one none', () => {
    const base = { dataUpdateCount: 0, errorUpdateCount: 0, dataUpdatedAt: 0, errorUpdatedAt: 0 };
    expect(advanceLedger(undefined, base).failures).toBe(0);
    expect(advanceLedger(undefined, { ...base, errorUpdateCount: 4, errorUpdatedAt: 5 }).failures).toBe(1);
    expect(advanceLedger(undefined, {
      dataUpdateCount: 2, errorUpdateCount: 4, dataUpdatedAt: 9, errorUpdatedAt: 5,
    }).failures).toBe(0);
  });
});

describe('what the queue and the journal poll, and what they do not', () => {
  it('applies the policy to the queue and to every journal variant', () => {
    for (const options of [queueQueryOptions(), queueQueryOptions('c1'), journalQueryOptions(), journalQueryOptions(RUN_ID, 'c1', false)]) {
      expect(options.refetchInterval).toBe(operationalListRefetchInterval);
      expect(options.refetchIntervalInBackground).toBe(false);
    }
    expect(OPERATIONAL_LIST_POLL.refetchIntervalInBackground).toBe(false);
  });

  it('keeps the focus refresh, which is how a hidden tab catches up', () => {
    expect(queueQueryOptions().refetchOnWindowFocus).toBe('always');
    expect(journalQueryOptions().refetchOnWindowFocus).toBe('always');
    expect(queueQueryOptions().staleTime).toBe(0);
  });

  it('leaves «Исполнители» alone: that screen belongs to another change', () => {
    const options: Record<string, unknown> = { ...workersQueryOptions() };
    expect(options.refetchInterval).toBeUndefined();
    expect(options.refetchIntervalInBackground).toBeUndefined();
  });
});
