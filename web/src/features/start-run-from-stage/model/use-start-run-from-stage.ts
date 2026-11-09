'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { RunCostConsent, RunStatus, StageId } from '@/shared/api';
import { queryKeys, startRunFromStage } from '@/shared/api';

export interface StartRunFromStageInput {
  readonly runId: string;
  readonly stageId: StageId;
  readonly idempotencyKey: string;
  readonly costConsent: RunCostConsent;
}

/** `startRunFromStage`: one intent, one key; the answer is the NEW run (the source is not touched). */
export function useStartRunFromStage() {
  const client = useQueryClient();
  return useMutation<RunStatus, unknown, StartRunFromStageInput>({
    mutationFn: async ({ runId, stageId, idempotencyKey, costConsent }) =>
      (await startRunFromStage({
        path: { run_id: runId }, body: { stage_id: stageId, cost_consent: costConsent }, idempotencyKey,
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
