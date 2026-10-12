'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { ExecutionWorker, WorkerId } from '@/shared/api';
import { queryKeys, setWorkerIntake } from '@/shared/api';

/**
 * `setWorkerIntake` (`W54-WORKERS-WEB`, plan §3.7): an administrator stops or allows a
 * worker taking new runs. The caller mints the key once per confirmed intent and passes the
 * same one on an explicit repeat; `retry: false`, so nothing here repeats a write on its own.
 * Runs a worker already holds are not affected, and no number the dashboard reads changes.
 */
export function useSetWorkerIntake() {
  const client = useQueryClient();
  return useMutation<ExecutionWorker, unknown,
    { workerId: WorkerId; enabled: boolean; idempotencyKey: string }>({
    mutationFn: async ({ workerId, enabled, idempotencyKey }) =>
      (await setWorkerIntake({
        path: { worker_id: workerId }, body: { enabled }, idempotencyKey,
      })).data,
    retry: false,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.execution.all() });
    },
  });
}
