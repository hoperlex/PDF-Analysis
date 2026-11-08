'use client';

import { queryOptions, useQuery } from '@tanstack/react-query';

import type { StageChainRun } from '@/shared/api';
import { listStageChangeCards } from '@/shared/api';
import { OPERATIONAL_LIST_POLLING } from '@/shared/config';

import { latestFullRun, runActive, STAGE_RUN_KEYS } from '../model/runs';
import { readRuns } from './reads';

/**
 * The runs of one pair as a row of the pairs catalog reads them (`UI-B-85`). The key is the one `StageRunControls` reads, so a
 * row and the controls opened under it share one request per pair.
 *
 * A row is read only while it is in view (`read`): the catalog lists up to a hundred pairs and each pair's runs are a walk of the
 * run list, so reading every row on open was a hundred walks. While a run of the pair moves the row is read again at the
 * operational cadence (`OPERATIONAL_LIST_POLLING`, ten seconds), never at the review cadence: the review cadence belongs to the
 * one pair the expert has open, which `StageRunControls` polls under the same key. A row out of view stops polling; its last
 * reading stays in the cache and is read again when the row comes back.
 */
export function pairRunsQueryOptions(pairId: string, read: boolean) {
  return queryOptions({
    queryKey: STAGE_RUN_KEYS.list(pairId),
    queryFn: () => readRuns(pairId),
    enabled: read,
    retry: false,
    refetchInterval: (query) => (query.state.data?.some(runActive) ? OPERATIONAL_LIST_POLLING.intervalMs : false),
  });
}

/** The counts of the cards of a pair's latest run: read once for a finished run, and only for a row in view. */
export function pairCardCountsQueryOptions(runId: string | undefined, read: boolean) {
  return queryOptions({
    queryKey: ['stage-run-card-counts', runId],
    queryFn: async () => (await listStageChangeCards({ path: { stage_chain_run_id: runId! }, query: { limit: 1 } })).data.counts,
    enabled: read && runId !== undefined,
    retry: false,
  });
}

/**
 * The latest full run of one pair and the counts of its cards: what a row of the pairs catalog says about the pair.
 * `inView` is required, not defaulted: a caller that renders one row per pair says which rows are on the screen, so no row
 * reads or polls unseen.
 */
export function useLatestPairRun(pairId: string, inView: boolean) {
  const runs = useQuery(pairRunsQueryOptions(pairId, inView));
  const run: StageChainRun | undefined = latestFullRun(runs.data ?? []);
  const counts = useQuery(pairCardCountsQueryOptions(run?.run_id, inView && run?.state === 'completed'));
  return { runs, run, counts };
}
