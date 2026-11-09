'use client';

/**
 * The commands on the stage layout (`HOSTS-WEB-01`, ADR-0028): save a new revision, and put the layout in force or take it
 * out. Each takes the idempotency key its caller minted for the intent and reuses it on an explicit repeat; `retry: false`.
 * Both invalidate `execution.all()` (the layout is filed under it, and so is the list of servers it is read against); neither
 * changes a number the dashboard reads. A revision changes nothing for runs already started: they froze their plan.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { ReviseStageModelLayoutRequest, StageModelLayout } from '@/shared/api';
import { queryKeys, reviseStageModelLayout, setStageModelLayoutEnabled } from '@/shared/api';

function useRefreshExecution() {
  const client = useQueryClient();
  return () => {
    void client.invalidateQueries({ queryKey: queryKeys.execution.all() });
  };
}

export function useReviseStageModelLayout() {
  const refresh = useRefreshExecution();
  return useMutation<StageModelLayout, unknown, { body: ReviseStageModelLayoutRequest; idempotencyKey: string }>({
    mutationFn: async ({ body, idempotencyKey }) => (await reviseStageModelLayout({ body, idempotencyKey })).data,
    retry: false,
    onSuccess: refresh,
  });
}

export function useSetStageModelLayoutEnabled() {
  const refresh = useRefreshExecution();
  return useMutation<StageModelLayout, unknown, { enabled: boolean; idempotencyKey: string }>({
    mutationFn: async ({ enabled, idempotencyKey }) =>
      (await setStageModelLayoutEnabled({ body: { enabled }, idempotencyKey })).data,
    retry: false,
    onSuccess: refresh,
  });
}
