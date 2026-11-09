'use client';

/**
 * The stages of a run, plan and fact (`getRunStages`, `HOSTS-SEAL-2`, ADR-0028): for each chip of the run the models it was
 * planned to run on (role, model, effort, answer limit, access and server) and what the journal says happened (state, calls,
 * tokens, cost, times). The rail's second line and the window «Этапы анализа раздела» read it.
 *
 * **The cadence is the status loop's, not a second one.** `pollRunStatus` re-reads a run after 2 s, then 1.5 times as long
 * after each reading, up to 15 s (`pollDelayMs`, `shared/config/polling`); this query asks at the same delays, counted by its
 * own readings, so a screen that polls the status and the stages asks the two about equally often. It polls only while the run
 * is open (`active`) and stops when it ends; when the run turns terminal it reads once more, so the facts the window keeps are
 * the final ones and not the last in-flight ones. A hidden tab is not polled (`refetchIntervalInBackground` stays off).
 *
 * The answer is a **view**, never the raw query: `loading`, `error` or `read`. A failed re-read that still holds an earlier
 * body is `read` (the last reading stands, as the extended review's does); `error` is only the absence of any reading. A
 * reader that has no stages draws what it drew before this query existed, and says so where the model is the run's.
 */

import { useQuery } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';

import type { RunId, RunStages } from '@/shared/api';
import { getRunStages } from '@/shared/api';
import { pollDelayMs } from '@/shared/config';

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

/**
 * How long to wait before the next reading, or `false` for none: the status loop's schedule while the run is open, counted from
 * the readings this query has received (the first re-read comes 2 s after the first reading, never at once).
 */
export function runStagesPollInterval(active: boolean, readings: number): number | false {
  return active ? pollDelayMs(Math.max(1, readings)) : false;
}

export type RunStagesView =
  | { readonly phase: 'loading' }
  | { readonly phase: 'error' }
  | { readonly phase: 'read'; readonly stages: RunStages };

export function useRunStages(runId: RunId, active: boolean): RunStagesView {
  const query = useQuery({
    ...runStagesQueryOptions(runId),
    refetchInterval: (current) => runStagesPollInterval(active, current.state.dataUpdateCount),
  });
  // The reading that ends the poll: the run was open and is not any more, so the facts are read once more, final.
  const wasActive = useRef(active);
  const refetch = query.refetch;
  useEffect(() => {
    if (wasActive.current && !active) void refetch();
    wasActive.current = active;
  }, [active, refetch]);

  if (query.data !== undefined) return { phase: 'read', stages: query.data };
  return query.isError ? { phase: 'error' } : { phase: 'loading' };
}
