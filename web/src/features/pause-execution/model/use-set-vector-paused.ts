'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { VectorControl } from '@/shared/api';
import { setVectorPaused } from '@/shared/api';
import { vectorControlKey } from '@/entities/execution';

/**
 * Pauses or resumes the vectors (`setVectorPaused`, administrator, keyed). The answer is the control as it now stands, so it
 * is written to the cache at once; the read then refreshes behind it. The caller mints one key per intent and reuses it on a
 * retry, as the queue's pause does.
 */
export function useSetVectorPaused() {
  const client = useQueryClient();
  return useMutation<VectorControl, unknown, { paused: boolean; idempotencyKey: string }>({
    mutationFn: async ({ paused, idempotencyKey }) =>
      (await setVectorPaused({ body: { paused }, idempotencyKey })).data,
    retry: false,
    onSuccess: (control) => {
      client.setQueryData(vectorControlKey(), control);
      void client.invalidateQueries({ queryKey: vectorControlKey() });
    },
  });
}
