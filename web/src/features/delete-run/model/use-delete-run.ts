'use client';

import { hashKey, useMutation, useQueryClient } from '@tanstack/react-query';

import type { RunId, RunStatus } from '@/shared/api';
import { ApiError, deleteRun, queryKeys } from '@/shared/api';

/**
 * `deleteRun`: the run leaves every list; its findings and the expert's decisions stay stored.
 *
 * One intent is one idempotency key, minted by the caller and reused on a retry. On success the lists of runs, the queue and the
 * dashboard are read again. The deleted run's own status is **not** read again at once: the run page is still open while it
 * navigates away, and a refetch would answer `404` into a page that is about to be left. It is only marked stale, so a later visit
 * reads it and gets that `404`. A `404` from the command itself means someone deleted the run first, so the lists are read again then too.
 */
export function useDeleteRun() {
  const client = useQueryClient();
  const refreshLists = (runId: string): void => {
    const ownHash = hashKey(queryKeys.runs.detail(runId as RunId));
    void client.invalidateQueries({ queryKey: queryKeys.runs.all(), predicate: (query) => query.queryHash !== ownHash });
    void client.invalidateQueries({ queryKey: queryKeys.execution.all() });
    void client.invalidateQueries({ queryKey: queryKeys.dashboard.summary() });
  };
  return useMutation<RunStatus, unknown, { runId: string; idempotencyKey: string }>({
    mutationFn: async ({ runId, idempotencyKey }) =>
      (await deleteRun({ path: { run_id: runId }, idempotencyKey })).data,
    retry: false,
    onSuccess: (run) => {
      // An invalidation filter, not a `useQuery` filling the key, which is what `query-key-shape.guard` keeps to the entity's one factory.
      const own = queryKeys.runs.detail(run.run_id);
      void client.invalidateQueries({ queryKey: own, refetchType: 'none' });
      refreshLists(run.run_id);
    },
    onError: (error, { runId }) => {
      if (error instanceof ApiError && error.errorCode === 'not_found') refreshLists(runId);
    },
  });
}
