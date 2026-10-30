'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { RunCostConsent, RunStatus } from '@/shared/api';
import { queryKeys, reauditRun } from '@/shared/api';

export function useReauditRun() {
  const client = useQueryClient();
  return useMutation<RunStatus, unknown, { runId: string; idempotencyKey: string; costConsent: RunCostConsent }>({
    mutationFn: async ({ runId, idempotencyKey, costConsent }) =>
      (await reauditRun({ path: { run_id: runId }, body: { cost_consent: costConsent }, idempotencyKey })).data,
    retry: false,
    onSuccess: (run) => {
      client.setQueryData(queryKeys.runs.detail(run.run_id), run);
      void client.invalidateQueries({ queryKey: queryKeys.execution.all() });
      void client.invalidateQueries({ queryKey: queryKeys.runs.all() });
      void client.invalidateQueries({ queryKey: queryKeys.dashboard.summary() });
    },
  });
}
