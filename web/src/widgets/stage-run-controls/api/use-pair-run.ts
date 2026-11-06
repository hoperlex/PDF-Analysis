'use client';

import { useQuery } from '@tanstack/react-query';

import type { StageChainRun } from '@/shared/api';
import { listStageChangeCards } from '@/shared/api';
import { STAGE_REVIEW_POLL_MS } from '@/shared/config';

import { latestFullRun, runActive, STAGE_RUN_KEYS } from '../model/runs';
import { readRuns } from './reads';

/**
 * The latest full run of one pair and the counts of its cards (`UI-B-85`): what a row of the pairs catalog says about the pair.
 * The keys are the ones `StageRunControls` reads, so a row and the controls opened under it share one request.
 */
export function useLatestPairRun(pairId: string) {
  const runs = useQuery({
    queryKey: STAGE_RUN_KEYS.list(pairId),
    queryFn: () => readRuns(pairId),
    retry: false,
    refetchInterval: (query) => (query.state.data?.some(runActive) ? STAGE_REVIEW_POLL_MS : false),
  });
  const run: StageChainRun | undefined = latestFullRun(runs.data ?? []);
  const counts = useQuery({
    queryKey: ['stage-run-card-counts', run?.run_id],
    queryFn: async () => (await listStageChangeCards({ path: { stage_chain_run_id: run!.run_id }, query: { limit: 1 } })).data.counts,
    enabled: run?.state === 'completed',
    retry: false,
  });
  return { runs, run, counts };
}
