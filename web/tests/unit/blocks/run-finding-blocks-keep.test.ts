/**
 * `listRunFindingBlocks` is read once per run, not once per opened finding (judge J3 F4, `D-353` (5)).
 *
 * The review screen mounts a new «Блоки замечания» strip for every finding the reader opens, and each strip observes the run's
 * one query. With the app's `staleTime` of 30 s every observer that mounted on older data read the server again, and the server
 * joins three whole documents per read. The cases drive real observers of the app's own query client (its defaults), with a
 * fake clock (only `Date`: staleness is read from it) and a stand-in `fetch` that counts the requests: a walk at human pace over a run that has ended costs one read; the
 * answers that can still change (a run that has not ended, a run whose state is not known, `not_produced`) still cost one per
 * mount after 30 s, because they are not a fact yet.
 *
 * Not for good (`D-472`): the server joins the run's own geometry with the version's NEWEST portal blocks, so even a produced answer of an
 * ended run can change when a later run re-produces the portal geometry, and nothing in the answer says so. It is kept for ten minutes,
 * then read again by the next strip that mounts and by the window getting the focus back.
 */

import { QueryObserver, environmentManager, focusManager } from '@tanstack/react-query';
import type { QueryClient } from '@tanstack/react-query';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

import { createQueryClient } from '@/_app/query-client';
import type { RunFindingBlockLinks, RunId, RunState } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { runFindingBlocksQueryOptions } from '@/entities/block';

import { RUN_ID, runStatus } from '../review/fixtures';
import { BLOCKS_VERSION_UID, blockId } from './fixtures';

const wasServer = environmentManager.isServer();
beforeAll(() => environmentManager.setIsServer(() => false));
afterAll(() => environmentManager.setIsServer(() => wasServer));
afterEach(() => focusManager.setFocused(undefined));

/** What a produced answer of an ended run is kept for (`D-472`); the code's own constant is private, and a change of it is a change to restate here. */
const KEPT_MS = 10 * 60_000;

const LINKS: RunFindingBlockLinks = {
  run_id: RUN_ID,
  version_uid: BLOCKS_VERSION_UID,
  status: 'produced',
  unlinked_pages: [],
  items: [{ finding_uid: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8A', portal_block_ids: [blockId(1)] }],
};

let reads = 0;
let answer: RunFindingBlockLinks = LINKS;

beforeEach(() => {
  reads = 0;
  answer = LINKS;
  vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', '/bff/v1');
  vi.stubGlobal('fetch', async () => {
    reads += 1;
    return new Response(JSON.stringify(answer), { status: 200, headers: { 'Content-Type': 'application/json' } });
  });
  vi.useFakeTimers({ toFake: ['Date'] });
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

/** The reader takes this long over a finding; the app's default would have called every earlier answer stale by then. */
const READING_TIME_MS = 45_000;
const later = (milliseconds: number): void => {
  vi.setSystemTime(new Date(Date.now() + milliseconds));
};

/** One strip of the review screen: mounts, reads what is there (or waits for the read it started), goes when the reader opens another finding. */
async function openAFinding(client: QueryClient, runId: RunId = RUN_ID as RunId): Promise<void> {
  const observer = new QueryObserver(client, runFindingBlocksQueryOptions(runId, client));
  const stop = observer.subscribe(() => {});
  await vi.waitFor(() => {
    expect(observer.getCurrentResult().isFetching).toBe(false);
  });
  stop();
}

async function walk(client: QueryClient, findings: number): Promise<void> {
  for (let opened = 0; opened < findings; opened += 1) {
    await openAFinding(client);
    later(READING_TIME_MS);
  }
}

function withRun(state: RunState | null): QueryClient {
  const client = createQueryClient();
  if (state !== null) client.setQueryData(queryKeys.runs.detail(RUN_ID as RunId), runStatus({ state }));
  return client;
}

describe('the links of a run that has ended', () => {
  it.each(['published', 'partial', 'failed', 'cancelled'] as const)('are read once however many findings are opened (%s)', async (state) => {
    await walk(withRun(state), 6);
    expect(reads).toBe(1);
  });

  it('is one query for the run: the key is the run’s, not a finding’s', () => {
    expect(runFindingBlocksQueryOptions(RUN_ID as RunId, createQueryClient()).queryKey).toEqual(queryKeys.runs.findingBlocks(RUN_ID as RunId));
    expect(JSON.stringify(runFindingBlocksQueryOptions(RUN_ID as RunId, createQueryClient()).queryKey)).not.toContain('fnd_');
  });

  it('is read again for another run: the answer of one run is not another’s', async () => {
    const client = withRun('published');
    await openAFinding(client);
    await openAFinding(client, 'run_01J9ZQ8K7NHVXW3T2R5M6P4QZZ' as RunId);
    expect(reads).toBe(2);
  });
});

describe('what is not yet a fact is still read again after the default 30 s', () => {
  it.each(['created', 'queued', 'running', 'validating'] as const)('the links of a run that has not ended (%s)', async (state) => {
    await walk(withRun(state), 3);
    expect(reads).toBe(3);
  });

  it('the links of a run whose state is not in the cache', async () => {
    await walk(withRun(null), 3);
    expect(reads).toBe(3);
  });

  it('a «not_produced» answer, which a later run of the version can turn into a produced one', async () => {
    answer = { ...LINKS, status: 'not_produced', items: [] };
    await walk(withRun('published'), 3);
    expect(reads).toBe(3);
  });

  it('and not before the 30 s are out, for any of them', async () => {
    const client = withRun('running');
    await openAFinding(client);
    later(10_000);
    await openAFinding(client);
    expect(reads).toBe(1);
  });
});

describe('a produced answer of an ended run is not kept for ever (`D-472`)', () => {
  it('is read again by the next strip once the ten minutes are out, and not before', async () => {
    const client = withRun('published');
    await openAFinding(client);
    later(KEPT_MS - 1_000);
    await openAFinding(client);
    expect(reads).toBe(1);
    later(2_000);
    await openAFinding(client);
    expect(reads).toBe(2);
  });

  it('is read again when the window gets the focus back after the ten minutes, and not before', async () => {
    const client = withRun('published');
    client.mount(); // what `QueryClientProvider` does: the client listens to the window's focus
    try {
      const observer = new QueryObserver(client, runFindingBlocksQueryOptions(RUN_ID as RunId, client));
      const stop = observer.subscribe(() => {});
      await vi.waitFor(() => expect(observer.getCurrentResult().isFetching).toBe(false));
      expect(reads).toBe(1);

      later(KEPT_MS - 1_000);
      focusManager.setFocused(false);
      focusManager.setFocused(true);
      await new Promise((resolve) => setTimeout(resolve, 25)); // real time: a refetch would have been counted by now
      expect(reads).toBe(1);

      later(2_000);
      focusManager.setFocused(false);
      focusManager.setFocused(true);
      await vi.waitFor(() => expect(reads).toBe(2));
      stop();
    } finally {
      client.unmount();
    }
  });

  it('asks for the read on focus itself: the app’s default is off', () => {
    const options = runFindingBlocksQueryOptions(RUN_ID as RunId, createQueryClient());
    expect(createQueryClient().getDefaultOptions().queries?.refetchOnWindowFocus).toBe(false);
    expect(options.refetchOnWindowFocus).toBe(true);
  });
});
