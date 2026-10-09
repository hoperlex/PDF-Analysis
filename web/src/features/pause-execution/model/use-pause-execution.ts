'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { ExecutionDispatchStatus } from '@/shared/api';
import { queryKeys, setExecutionPaused } from '@/shared/api';

export function usePauseExecution() {
  const client = useQueryClient();
  return useMutation<ExecutionDispatchStatus, unknown,
    { paused: boolean; idempotencyKey: string }>({
    mutationFn: async ({ paused, idempotencyKey }) =>
      (await setExecutionPaused({ body: { paused }, idempotencyKey })).data,
    retry: false,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.execution.all() });
    },
  });
}
