'use client';

import { useQuery } from '@tanstack/react-query';

import type {
  ExecutionJournalPage, ExecutionQueuePage, ExecutionWorkerPage, RunId,
} from '@/shared/api';
import { listExecutionJournal, listExecutionQueue, listWorkers, queryKeys } from '@/shared/api';

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

/** One page of the «Исполнители» screen. */
export const WORKER_PAGE_LIMIT = 50;

/**
 * The first page the queue and run screens read to name a run's worker: the contract's
 * largest page. Newest start first, so the workers that can hold a run — the ones still
 * heartbeating — come before the accumulated offline rows; past it, `runWorker` says so.
 */
export const WORKER_LOOKUP_LIMIT = 200;

/*
 * The same freshness rule as the queue and the journal (`C-26`): a worker's state is the
 * thing an operator opens this screen to see now. Refreshed on focus, after an intake
 * command (`queryKeys.execution.all()`), and by «Обновить».
 */
export function workersQueryOptions(cursor?: string, limit = WORKER_PAGE_LIMIT, enabled = true) {
  return {
    queryKey: queryKeys.execution.workers(cursor, limit),
    queryFn: async () => (await listWorkers({
      query: { limit, ...(cursor === undefined ? {} : { cursor }) },
    })).data,
    refetchOnWindowFocus: 'always',
    staleTime: 0,
    enabled,
  } as const;
}

export function useWorkers(cursor?: string) {
  return useQuery<ExecutionWorkerPage>(workersQueryOptions(cursor));
}

/** The first `WORKER_LOOKUP_LIMIT` workers, read only while some run can hold one. */
export function useWorkerLookup(enabled: boolean) {
  return useQuery<ExecutionWorkerPage>(workersQueryOptions(undefined, WORKER_LOOKUP_LIMIT, enabled));
}
