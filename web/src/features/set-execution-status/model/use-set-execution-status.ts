'use client';

/**
 * Set or clear the execution status of one accepted finding (`R-151g`, `setFindingExecutionStatus`). One key per
 * intent, reused on a retry; on success the run's findings and the finding are re-read so the badge moves at once.
 */

import { useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { FindingExecutionState, FindingExecutionStatus, FindingUid, RunId } from '@/shared/api';
import { newIdempotencyKey, queryKeys, setFindingExecutionStatus } from '@/shared/api';

export function useSetExecutionStatus({ findingUid, runId }: { readonly findingUid: FindingUid; readonly runId: RunId }) {
  const client = useQueryClient();
  const keys = useRef(new Map<string, string>());
  return useMutation<FindingExecutionState, unknown, { readonly status: FindingExecutionStatus | null }>({
    mutationFn: async ({ status }) => {
      const intent = `${findingUid}:${status ?? 'none'}`;
      const key = keys.current.get(intent) ?? newIdempotencyKey();
      keys.current.set(intent, key);
      return (await setFindingExecutionStatus({
        path: { finding_uid: findingUid },
        body: { status },
        idempotencyKey: key,
      })).data;
    },
    retry: false,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.runs.findings(runId) });
      void client.invalidateQueries({ queryKey: queryKeys.findings.detail(findingUid) });
    },
  });
}
