'use client';

/**
 * The stages of a run, plan and fact (`getRunStages`, `HOSTS-SEAL-2`, ADR-0028): for each chip of the run the models it was
 * planned to run on (role, model, effort, answer limit, access and server) and what the journal says happened (state, calls,
 * tokens, cost, times). The rail's second line and the window «Этапы анализа раздела» read it.
 *
 * **It has no clock of its own.** The one run-progress loop (`pollRunStatus`, 2 s, then 1.5 times as long after each reading, up
 * to 15 s) is the only cadence the application has for a run, and `useRunStatus` files each of its readings with
 * `recordRunReading`, which marks this query stale; a mounted reader then reads it again, once for each reading of the run. So
 * the stages are asked about exactly as often as the status is, while the run is open; the reading that ends the loop is the
 * last, and it is the one that makes the facts final. Nothing here sets an interval, so a hidden second cadence cannot appear
 * (`tests/unit/run/polling.test.ts` holds that). The same is true of the journal of the run, which `recordRunReading` marks stale
 * the same way.
 *
 * The answer is a **view**, never the raw query: `loading`, `error` or `read`. A failed re-read that still holds an earlier
 * body is `read` (the last reading stands, as the extended review's does); `error` is only the absence of any reading. A
 * reader that has no stages draws what it drew before this query existed, and says so where the model is the run's. `enabled`
 * is false until the run itself has been read: a run that is not found has no stages to ask for.
 */

import { useQuery } from '@tanstack/react-query';

import type { RunId, RunStages } from '@/shared/api';
import { getRunStages } from '@/shared/api';

/** One key per run. It sits under `runs`, so a reader that drops every run's reads drops these too. */
export const runStagesKey = (runId: RunId) => ['runs', 'stages', runId] as const;

export function runStagesQueryOptions(runId: RunId) {
  return {
    queryKey: runStagesKey(runId),
    queryFn: async ({ signal }: { signal: AbortSignal }): Promise<RunStages> =>
      (await getRunStages({ path: { run_id: runId } }, { signal })).data,
    retry: false,
  } as const;
}

export type RunStagesView =
  | { readonly phase: 'loading' }
  | { readonly phase: 'error' }
  | { readonly phase: 'read'; readonly stages: RunStages };

export function useRunStages(runId: RunId, enabled: boolean): RunStagesView {
  const query = useQuery({ ...runStagesQueryOptions(runId), enabled });
  if (query.data !== undefined) return { phase: 'read', stages: query.data };
  return query.isError ? { phase: 'error' } : { phase: 'loading' };
}
