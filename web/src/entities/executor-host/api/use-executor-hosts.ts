'use client';

import { useQuery } from '@tanstack/react-query';

import type { ExecutorHostDetails, ExecutorHostId, ExecutorHostList, Role } from '@/shared/api';
import { getExecutorHostDetails, listExecutorHosts, queryKeys } from '@/shared/api';
import { OPERATIONAL_LIST_POLL } from '@/entities/execution';

/**
 * The reads of «Серверы» (`HOSTS-WEB-01`, plan 2026-11-09 §6: the web polls every 10 seconds while the screen is open).
 *
 * Both are filed under `execution`, so every command on a server (`queryKeys.execution.all()`) refreshes them. The list is read
 * on the operational-list cadence, `OPERATIONAL_LIST_POLL` (10 s while the tab is visible, backed off after a failure, none
 * while the tab is hidden), and again on tab return and by «Обновить». The details are derived at read time and are read only
 * while an administrator has them open.
 *
 * **The viewer reads neither** (`R-150w`): `listExecutorHosts` and `getExecutorHostDetails` refuse the role, so the screen asks
 * `mayReadHosts(roles)` before it enables a read, and a role that is not an expert's or an administrator's never sends one.
 */

export function mayReadHosts(roles: readonly Role[]): boolean {
  return roles.includes('admin') || roles.includes('expert');
}

export const executorHostsKey = (): readonly unknown[] => [...queryKeys.execution.all(), 'hosts'];
export const executorHostDetailsKey = (hostId: ExecutorHostId): readonly unknown[] =>
  [...queryKeys.execution.all(), 'host-details', hostId];

export function executorHostsQueryOptions(enabled = true) {
  return {
    queryKey: executorHostsKey(),
    queryFn: async () => (await listExecutorHosts({})).data,
    ...OPERATIONAL_LIST_POLL,
    refetchOnWindowFocus: 'always',
    staleTime: 0,
    enabled,
  } as const;
}

export function useExecutorHosts(enabled = true) {
  return useQuery<ExecutorHostList>(executorHostsQueryOptions(enabled));
}

export function executorHostDetailsQueryOptions(hostId: ExecutorHostId, enabled = true) {
  return {
    queryKey: executorHostDetailsKey(hostId),
    queryFn: async () => (await getExecutorHostDetails({ path: { host_id: hostId } })).data,
    refetchOnWindowFocus: 'always',
    staleTime: 0,
    enabled,
  } as const;
}

/** «Подробнее» of one server (administrator). */
export function useExecutorHostDetails(hostId: ExecutorHostId, enabled = true) {
  return useQuery<ExecutorHostDetails>(executorHostDetailsQueryOptions(hostId, enabled));
}
