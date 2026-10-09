'use client';

import { useQuery } from '@tanstack/react-query';

import type { ExecutionJournalPage, ExecutionQueuePage, RunId } from '@/shared/api';
import { listExecutionJournal, listExecutionQueue, queryKeys } from '@/shared/api';

export const EXECUTION_PAGE_LIMIT = 25;

export function queueQueryOptions(cursor?: string) {
  return {
    queryKey: queryKeys.execution.queue(cursor),
    queryFn: async () => (await listExecutionQueue({
      query: { limit: EXECUTION_PAGE_LIMIT, ...(cursor === undefined ? {} : { cursor }) },
    })).data,
    refetchOnWindowFocus: 'always',
  } as const;
}

export function useExecutionQueue(cursor?: string) {
  return useQuery<ExecutionQueuePage>(queueQueryOptions(cursor));
}

export function journalQueryOptions(runId?: RunId, cursor?: string, enabled = true) {
  return {
    queryKey: queryKeys.execution.journal(runId, cursor),
    queryFn: async () => (await listExecutionJournal({
      query: {
        limit: EXECUTION_PAGE_LIMIT,
        ...(runId === undefined ? {} : { run_id: runId }),
        ...(cursor === undefined ? {} : { cursor }),
      },
    })).data,
    refetchOnWindowFocus: 'always',
    enabled,
  } as const;
}

export function useExecutionJournal(runId?: RunId, cursor?: string, enabled = true) {
  return useQuery<ExecutionJournalPage>(journalQueryOptions(runId, cursor, enabled));
}
