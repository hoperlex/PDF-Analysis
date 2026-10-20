'use client';

import { useQuery } from '@tanstack/react-query';

import type { RunId, RunNormReferences } from '@/shared/api';
import { getRunNormReferences, queryKeys } from '@/shared/api';

/**
 * `getRunNormReferences` (`NORM-REFS-RUN-01`): the normative documents a run's saved text
 * cites, each resolved against the norms snapshot the run pinned, or the state that stops it.
 *
 * The answer is always a `RunNormReferences`: a run that pinned no snapshot, has no saved text
 * layer or cites more designations than one answer carries is its `state`, not a failure. A
 * failure is what the transport refuses (`404` for an unknown run). The server computes the
 * list per request from stored facts and writes nothing, so a refetch is always safe.
 */
export function runNormReferencesQueryOptions(runId: RunId) {
  return {
    queryKey: queryKeys.runs.normReferences(runId),
    queryFn: async (): Promise<RunNormReferences> =>
      (await getRunNormReferences({ path: { run_id: runId } })).data,
  } as const;
}

export function useRunNormReferences(runId: RunId) {
  return useQuery<RunNormReferences>(runNormReferencesQueryOptions(runId));
}
