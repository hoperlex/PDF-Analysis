'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { RunStatus } from '@/shared/api';
import { cancelRun, queryKeys } from '@/shared/api';

export function useCancelRun() {
  const client = useQueryClient();
  return useMutation<RunStatus, unknown, { runId: string; idempotencyKey: string }>({
    mutationFn: async ({ runId, idempotencyKey }) =>
      (await cancelRun({ path: { run_id: runId }, idempotencyKey })).data,
    retry: false,
    onSuccess: (run) => {
      client.setQueryData(queryKeys.runs.detail(run.run_id), run);
      void client.invalidateQueries({ queryKey: queryKeys.execution.all() });
      void client.invalidateQueries({ queryKey: queryKeys.runs.all() });
      void client.invalidateQueries({ queryKey: queryKeys.dashboard.summary() });
    },
  });
}
