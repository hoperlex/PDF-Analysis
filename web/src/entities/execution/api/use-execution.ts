'use client';

import { useQuery } from '@tanstack/react-query';

import type { ExecutionJournalPage, ExecutionQueuePage, RunId } from '@/shared/api';
import { listExecutionJournal, listExecutionQueue, queryKeys } from '@/shared/api';

export const EXECUTION_PAGE_LIMIT = 25;

/*
 * `C-26`: both reads are stale the moment they settle (`staleTime: 0`). The application's
 * default `staleTime: 30_000` would otherwise let a remount, a tab return or a navigation back
 * to the queue or the journal show a page up to thirty seconds old although each of them is
 * the screen an operator opens to see what the runner is doing now.
 */

export function queueQueryOptions(cursor?: string) {
  return {
    queryKey: queryKeys.execution.queue(cursor),
    queryFn: async () => (await listExecutionQueue({
      query: { limit: EXECUTION_PAGE_LIMIT, ...(cursor === undefined ? {} : { cursor }) },
    })).data,
    refetchOnWindowFocus: 'always',
    staleTime: 0,
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
    staleTime: 0,
    enabled,
  } as const;
}

export function useExecutionJournal(runId?: RunId, cursor?: string, enabled = true) {
  return useQuery<ExecutionJournalPage>(journalQueryOptions(runId, cursor, enabled));
}
