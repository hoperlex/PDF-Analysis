'use client';

import { useQueries, useQuery } from '@tanstack/react-query';

import type {
  ExecutorConnectionDetail,
  ExecutorConnectionId,
  ExecutorConnectionList,
  ExecutorRouteList,
} from '@/shared/api';
import { getExecutorConnection, listExecutorConnections, listExecutorRoutes, queryKeys } from '@/shared/api';

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

export function connectionDetailQueryOptions(connectionId: ExecutorConnectionId, enabled = true) {
  return {
    queryKey: queryKeys.execution.connection(connectionId),
    queryFn: async () => (await getExecutorConnection({ path: { connection_id: connectionId } })).data,
    refetchOnWindowFocus: 'always',
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
