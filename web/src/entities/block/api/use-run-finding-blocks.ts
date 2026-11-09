'use client';

/**
 * `listRunFindingBlocks` — the portal blocks that hold each finding of a run (`UI-PARITY-C6`, contract 1.41.0).
 *
 * One read per run: the relation is derived on the server from the run's saved text-layer geometry and the version's
 * portal blocks, both fixed once the run is stored. It is a separate read from `listRunFindings` on purpose: the findings
 * are the product, the link is a view over them, and a link that cannot be derived must not take the findings list down
 * with it.
 *
 * **How long it is kept** (`D-353` (5), judge J3 F4; `D-472`). The key is the run's, not a finding's, but the app's default of 30 s
 * made every observer that mounted on older data read it again, and the server joins three whole documents per read: the
 * review screen mounts a fresh strip for each finding the reader opens, so a walk at human pace cost one whole-document
 * read per click. So an answer is kept longer when it is as settled as it gets: `status: 'produced'` **and** the run is in a
 * terminal state. A `not_produced` answer is not kept longer than the default (a later run of the version can produce the
 * portal geometry it lacked), nor is any answer of a run that has not ended (its findings are not all published). The run's
 * state is read from the cache of the run's own status, which the screens that use this hook already hold; a run whose status
 * is not in the cache is not known to be terminal and keeps the default.
 *
 * **Not for good.** The run's half of the join is fixed, but the portal half is the version's NEWEST portal blocks, so a later
 * run that re-produces the portal geometry changes the answer for an older run, and the answer carries nothing the client could
 * key on to see it (no source run, no digest). So the longer time is finite (ten minutes, which a walk through the findings
 * of one run at human pace stays inside) and the read is repeated when the window gets the focus again after it
 * (`refetchOnWindowFocus`: the app's default is off; React Query refreshes only an answer that is stale), so a page left open
 * does not go on showing the earlier answer until it is reloaded.
 */

import type { Query, QueryClient } from '@tanstack/react-query';
import { useQuery, useQueryClient } from '@tanstack/react-query';

import type { RunFindingBlockLinks, RunId } from '@/shared/api';
import { isTerminalRunState, listRunFindingBlocks, queryKeys } from '@/shared/api';

/** The app's own default (`_app/query-client.ts`), restated: what an answer that may still change is kept for. */
const MAY_STILL_CHANGE_MS = 30_000;

/** What a produced answer of an ended run is kept for (`D-472`): long enough for a walk through its findings, not for ever. */
const SETTLED_ANSWER_KEPT_MS = 10 * 60_000;

/**
 * The read of one run's links, ready for `useQuery`, an observer or a prefetch. `client` is asked, each time an observer
 * decides whether the cached answer is still fresh, whether the run has ended (see the header).
 */
export function runFindingBlocksQueryOptions(runId: RunId, client: QueryClient) {
  return {
    queryKey: queryKeys.runs.findingBlocks(runId),
    queryFn: async ({ signal }: { signal: AbortSignal }): Promise<RunFindingBlockLinks> =>
      (await listRunFindingBlocks({ path: { run_id: runId } }, { signal })).data,
    staleTime: (query: Query<RunFindingBlockLinks>): number => {
      const state = client.getQueryData(queryKeys.runs.detail(runId))?.state;
      return query.state.data?.status === 'produced' && state !== undefined && isTerminalRunState(state)
        ? SETTLED_ANSWER_KEPT_MS
        : MAY_STILL_CHANGE_MS;
    },
    // The app's default is off; with it on, a stale answer is read again when the reader comes back to the window (`D-472`).
    refetchOnWindowFocus: true,
  };
}

/** `runId` of `null`, or `enabled: false`, asks nothing. */
export function useRunFindingBlocks(runId: RunId | null, enabled = true) {
  const client = useQueryClient();
  return useQuery<RunFindingBlockLinks>({
    ...runFindingBlocksQueryOptions((runId ?? '') as RunId, client),
    enabled: runId !== null && enabled,
  });
}
