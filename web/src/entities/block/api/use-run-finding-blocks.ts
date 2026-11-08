'use client';

/**
 * `listRunFindingBlocks` — the portal blocks that hold each finding of a run (`UI-PARITY-C6`, contract 1.41.0).
 *
 * One read per run: the relation is derived on the server from the run's saved text-layer geometry and the version's
 * portal blocks, both fixed once the run is stored, so the answer is kept as the run's findings are. It is a separate
 * read from `listRunFindings` on purpose: the findings are the product, the link is a view over them, and a link that
 * cannot be derived must not take the findings list down with it.
 */

import { useQuery } from '@tanstack/react-query';

import type { RunFindingBlockLinks, RunId } from '@/shared/api';
import { listRunFindingBlocks, queryKeys } from '@/shared/api';

/** `runId` of `null`, or `enabled: false`, asks nothing. */
export function useRunFindingBlocks(runId: RunId | null, enabled = true) {
  return useQuery<RunFindingBlockLinks>({
    queryKey: queryKeys.runs.findingBlocks((runId ?? '') as RunId),
    enabled: runId !== null && enabled,
    queryFn: async ({ signal }) => (await listRunFindingBlocks({ path: { run_id: runId as RunId } }, { signal })).data,
  });
}
