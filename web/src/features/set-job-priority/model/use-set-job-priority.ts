'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { ExecutionQueueItem } from '@/shared/api';
import { queryKeys, setJobPriority } from '@/shared/api';

export function useSetJobPriority() {
  const client = useQueryClient();
  return useMutation<ExecutionQueueItem, unknown,
    { jobId: string; priority: number; idempotencyKey: string }>({
    mutationFn: async ({ jobId, priority, idempotencyKey }) =>
      (await setJobPriority({
        path: { job_id: jobId }, body: { priority }, idempotencyKey,
      })).data,
    retry: false,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.execution.all() });
    },
  });
}
