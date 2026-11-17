'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { RestartPoint, RunCostConsent, RunStatus } from '@/shared/api';
import { queryKeys, restartRun } from '@/shared/api';

export interface RestartRunInput {
  readonly runId: string;
  readonly point: RestartPoint;
  readonly idempotencyKey: string;
  readonly costConsent: RunCostConsent;
}

/** `restartRun`: one intent, one key; the answer is the NEW run (the source stays as it was until the new run publishes, `R-155g`). */
export function useRestartRun() {
  const client = useQueryClient();
  return useMutation<RunStatus, unknown, RestartRunInput>({
    mutationFn: async ({ runId, point, idempotencyKey, costConsent }) =>
      (await restartRun({
        path: { run_id: runId }, body: { restart_point: point, cost_consent: costConsent }, idempotencyKey,
      })).data,
    retry: false,
    onSuccess: (run) => {
      client.setQueryData(queryKeys.runs.detail(run.run_id), run);
      void client.invalidateQueries({ queryKey: queryKeys.execution.all() });
      void client.invalidateQueries({ queryKey: queryKeys.runs.all() });
      void client.invalidateQueries({ queryKey: queryKeys.dashboard.summary() });
    },
  });
}
