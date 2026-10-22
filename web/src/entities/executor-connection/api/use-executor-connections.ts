'use client';

import { useQueries, useQuery } from '@tanstack/react-query';

import type {
  ExecutorConnectionDetail,
  ExecutorConnectionId,
  ExecutorConnectionList,
  ExecutorRouteList,
} from '@/shared/api';
import { getExecutorConnection, listExecutorConnections, listExecutorRoutes, queryKeys } from '@/shared/api';

import { RUNNER_POLL_MS, hasLiveRunnerToken } from '../model/runner-tokens';

/*
 * The same freshness rule as the worker registry (`C-26`): a connection's probe is the thing
 * an administrator opens this tab to see now, so every read is stale the moment it settles,
 * refreshes on tab return, after a command (`queryKeys.execution.all()`) and by «Обновить».
 */

export function connectionsQueryOptions() {
  return {
    queryKey: queryKeys.execution.connections(),
    queryFn: async () => (await listExecutorConnections({})).data,
    refetchOnWindowFocus: 'always',
    staleTime: 0,
  } as const;
}

export function useExecutorConnections() {
  return useQuery<ExecutorConnectionList>(connectionsQueryOptions());
}

/** How often a connection is read again while one of its probes is still open. */
export const PROBE_POLL_MS = 3000;

/**
 * A probe is open from the moment it is requested until a worker finishes it, or the server
 * ends it as `no_worker` after 120 seconds. While one is open the detail is read again every
 * few seconds, so the outcome appears without the person asking for it.
 */
export function hasOpenProbe(detail: ExecutorConnectionDetail | undefined): boolean {
  if (detail === undefined) return false;
  return (
    detail.probes.some((probe) => probe.state !== 'finished') ||
    detail.revisions.some((revision) => revision.latest_probe !== undefined && revision.latest_probe.state !== 'finished')
  );
}

export function connectionDetailQueryOptions(connectionId: ExecutorConnectionId, enabled = true) {
  return {
    queryKey: queryKeys.execution.connection(connectionId),
    queryFn: async () => (await getExecutorConnection({ path: { connection_id: connectionId } })).data,
    refetchOnWindowFocus: 'always',
    // A probe in flight is read every few seconds; a `pull` connection with a live runner token
    // every ten, so «на связи» and the open tasks follow the runner without a page reload.
    refetchInterval: (query: { state: { data: ExecutorConnectionDetail | undefined } }) =>
      hasOpenProbe(query.state.data)
        ? PROBE_POLL_MS
        : hasLiveRunnerToken(query.state.data, Date.now()) ? RUNNER_POLL_MS : false,
    staleTime: 0,
    enabled,
  } as const;
}

export function useExecutorConnectionDetail(connectionId: ExecutorConnectionId, enabled = true) {
  return useQuery<ExecutorConnectionDetail>(connectionDetailQueryOptions(connectionId, enabled));
}

/** The detail of several connections at once, keyed by id. A detail not yet read is absent. */
export function useExecutorConnectionDetails(connectionIds: readonly ExecutorConnectionId[]) {
  return useQueries({
    queries: connectionIds.map((id) => connectionDetailQueryOptions(id)),
    combine: (results) => ({
      details: new Map(
        results.flatMap((result, index): [string, ExecutorConnectionDetail][] => {
          const id = connectionIds[index];
          return id !== undefined && result.data !== undefined ? [[id, result.data]] : [];
        }),
      ),
      failed: results.some((result) => result.isError),
      pending: results.some((result) => result.isPending),
    }),
  });
}

export function routesQueryOptions() {
  return {
    queryKey: queryKeys.execution.routes(),
    queryFn: async () => (await listExecutorRoutes({})).data,
    refetchOnWindowFocus: 'always',
    staleTime: 0,
  } as const;
}

export function useExecutorRoutes() {
  return useQuery<ExecutorRouteList>(routesQueryOptions());
}
