'use client';

import { useQuery } from '@tanstack/react-query';

import type {
  ExecutionDispatchStatus, ExecutionJournalPage, ExecutionQueuePage, ExecutionWorkerPage, ListExecutionQueueInput,
  RunId,
} from '@/shared/api';
import { getExecutionDispatch, listExecutionJournal, listExecutionQueue, listWorkers, queryKeys } from '@/shared/api';

import { OPERATIONAL_LIST_POLL, autoRefreshMeta } from './operational-poll';

export const EXECUTION_PAGE_LIMIT = 25;

/*
 * `C-26`: both reads are stale the moment they settle (`staleTime: 0`). The application's
 * default `staleTime: 30_000` would otherwise let a remount, a tab return or a navigation back
 * to the queue or the journal show a page up to thirty seconds old although each of them is
 * the screen an operator opens to see what the runner is doing now.
 *
 * They also refresh themselves on the `OPERATIONAL_LIST_POLLING` cadence (`operational-poll.ts`):
 * while the tab is visible, backing off after a failed read. The worker list of «Исполнители»
 * follows the same policy (below).
 */

/** The job states `listExecutionQueue` filters by, as the contract declares them. */
export type ExecutionQueueState = NonNullable<NonNullable<ListExecutionQueueInput['query']>['state']>;

/** `D-370` (contract 1.43.0): the queue's three groups of states, as `listExecutionQueue` names them (`state_group`). */
export type ExecutionQueueStateGroup = NonNullable<NonNullable<ListExecutionQueueInput['query']>['state_group']>;

/**
 * What narrows the queue (`UI-PARITY-QUEUE-A`). `state` keeps the jobs in one state and `stateGroup` (`D-370`) the jobs in any
 * state of one group — the server refuses the two together, so a filter holds one of them; the period
 * `[createdFrom, createdTo)` keeps the jobs accepted in it, both as instants with an offset. Unset means no
 * filter. The server binds a cursor to the filters it was issued under, so a filter and its cursors
 * change together (the page resets its cursors when the filter moves) and are one cache key.
 */
export interface ExecutionQueueFilter {
  readonly state?: ExecutionQueueState;
  readonly stateGroup?: ExecutionQueueStateGroup;
  readonly createdFrom?: string;
  readonly createdTo?: string;
}

export function queueQueryOptions(cursor?: string, filter: ExecutionQueueFilter = {}) {
  return {
    queryKey: queryKeys.execution.queue(cursor, filter),
    queryFn: async () => (await listExecutionQueue({
      query: {
        limit: EXECUTION_PAGE_LIMIT,
        ...(cursor === undefined ? {} : { cursor }),
        ...(filter.state === undefined ? {} : { state: filter.state }),
        ...(filter.stateGroup === undefined ? {} : { state_group: filter.stateGroup }),
        ...(filter.createdFrom === undefined ? {} : { created_from: filter.createdFrom }),
        ...(filter.createdTo === undefined ? {} : { created_to: filter.createdTo }),
      },
    })).data,
    ...OPERATIONAL_LIST_POLL,
    refetchOnWindowFocus: 'always',
    staleTime: 0,
  } as const;
}

export function useExecutionQueue(cursor?: string, filter: ExecutionQueueFilter = {}) {
  return useQuery<ExecutionQueuePage>(queueQueryOptions(cursor, filter));
}

/**
 * The installation's pause state (`getExecutionDispatch`, `UI-PARITY-P0E`, ruling `R-151f`). The top strip
 * reads it on every screen, so it follows the operational-list cadence: re-read while the tab is visible,
 * backing off after a failure, never in the background. `enabled` is false for a session the queue is closed
 * to (the server refuses the read to `viewer`, `R-150w`).
 */
export function dispatchQueryOptions(enabled = true) {
  return {
    queryKey: queryKeys.execution.dispatch(),
    queryFn: async () => (await getExecutionDispatch({})).data,
    ...OPERATIONAL_LIST_POLL,
    refetchOnWindowFocus: 'always',
    staleTime: 0,
    enabled,
  } as const;
}

export function useExecutionDispatch(enabled = true) {
  return useQuery<ExecutionDispatchStatus>(dispatchQueryOptions(enabled));
}

/**
 * The journal read. `autoRefresh` is the screen's «Автообновление» (`UI-B-43`): on, the read follows the
 * operational-list cadence and the focus refresh like the queue; off, the screen reads once, on opening, on a
 * page change and on «Обновить», so the rows an operator is reading or copying do not move. It is the mode of
 * the same data, so it is not part of the key.
 */
export function journalQueryOptions(runId?: RunId, cursor?: string, enabled = true, autoRefresh = true) {
  return {
    queryKey: queryKeys.execution.journal(runId, cursor),
    queryFn: async () => (await listExecutionJournal({
      query: {
        limit: EXECUTION_PAGE_LIMIT,
        ...(runId === undefined ? {} : { run_id: runId }),
        ...(cursor === undefined ? {} : { cursor }),
      },
    })).data,
    ...OPERATIONAL_LIST_POLL,
    refetchOnWindowFocus: autoRefresh ? 'always' : false,
    staleTime: 0,
    enabled,
    meta: autoRefreshMeta(autoRefresh),
  } as const;
}

export function useExecutionJournal(runId?: RunId, cursor?: string, enabled = true, autoRefresh = true) {
  return useQuery<ExecutionJournalPage>(journalQueryOptions(runId, cursor, enabled, autoRefresh));
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
 * The same freshness and refresh rule as the queue and the journal (`C-26`, D-307): a worker's
 * state is the thing an operator opens this screen to see now. Refreshed on the
 * `OPERATIONAL_LIST_POLLING` cadence while the tab is visible, on focus, after an intake command
 * (`queryKeys.execution.all()`), and by «Обновить». The larger lookup page that the queue and the
 * run screen read to name a run's worker is the same query shape, so it follows the same cadence
 * while one of those screens is open.
 */
export function workersQueryOptions(cursor?: string, limit = WORKER_PAGE_LIMIT, enabled = true) {
  return {
    queryKey: queryKeys.execution.workers(cursor, limit),
    queryFn: async () => (await listWorkers({
      query: { limit, ...(cursor === undefined ? {} : { cursor }) },
    })).data,
    ...OPERATIONAL_LIST_POLL,
    refetchOnWindowFocus: 'always',
    staleTime: 0,
    enabled,
  } as const;
}

/** One page of the registry. `enabled` is `false` while the screen shows a tab that does not list workers. */
export function useWorkers(cursor?: string, enabled = true) {
  return useQuery<ExecutionWorkerPage>(workersQueryOptions(cursor, WORKER_PAGE_LIMIT, enabled));
}

/** The first `WORKER_LOOKUP_LIMIT` workers, read only while some run can hold one. */
export function useWorkerLookup(enabled: boolean) {
  return useQuery<ExecutionWorkerPage>(workersQueryOptions(undefined, WORKER_LOOKUP_LIMIT, enabled));
}
