'use client';

/**
 * The reads of «Группы» and «Правила» (`EXEC2-WEB-GROUPS-01`, ADR-0026 decisions 10, 11 and 17):
 * the groups with their current revision, the capacity of one group, the current rule of each
 * work kind with the routing mode, and the proposed cut-over.
 *
 * Every key stays under the `execution` root, built from `queryKeys.execution.all()` as the
 * agent-install read does. Every command on a group, a rule or the mode invalidates that root, and
 * «Обновить» on the «Исполнители» screen reads again whatever the open tab shows, so none of the
 * keys here needs a registry entry of its own. Every read is stale the moment it settles and
 * refreshes on tab return: an administrator opens these tabs to see the state now.
 *
 * The cut-over proposal is a read that exists only while the cut-over panel is open. It is not
 * kept (`gcTime: 0`) and never read twice on focus: `preview_digest` binds the proposal, and a
 * confirmation carrying a digest that is no longer the one now computed is refused as stale.
 */

import { useQuery } from '@tanstack/react-query';

import type {
  ExecutorGroupCapacity,
  ExecutorGroupId,
  ExecutorGroupList,
  ExecutorRoutingPreview,
  ExecutorRoutingRuleList,
} from '@/shared/api';
import {
  getExecutorGroupCapacity,
  listExecutorGroups,
  listExecutorRoutingRules,
  previewExecutorRouting,
  queryKeys,
} from '@/shared/api';

export function executorGroupsKey() {
  return [...queryKeys.execution.all(), 'groups'] as const;
}

export function executorGroupCapacityKey(groupId: ExecutorGroupId) {
  return [...queryKeys.execution.all(), 'group-capacity', groupId] as const;
}

export function executorRoutingRulesKey() {
  return [...queryKeys.execution.all(), 'routing-rules'] as const;
}

export function executorRoutingPreviewKey() {
  return [...queryKeys.execution.all(), 'routing-preview'] as const;
}

export function executorGroupsQueryOptions() {
  return {
    queryKey: executorGroupsKey(),
    queryFn: async () => (await listExecutorGroups({})).data,
    refetchOnWindowFocus: 'always',
    staleTime: 0,
  } as const;
}

/** Every group with its current revision, archived ones included. */
export function useExecutorGroups() {
  return useQuery<ExecutorGroupList>(executorGroupsQueryOptions());
}

export function executorGroupCapacityQueryOptions(groupId: ExecutorGroupId, enabled = true) {
  return {
    queryKey: executorGroupCapacityKey(groupId),
    queryFn: async () => (await getExecutorGroupCapacity({ path: { group_id: groupId } })).data,
    refetchOnWindowFocus: 'always',
    staleTime: 0,
    enabled,
  } as const;
}

/** The capacity of the current revision of one group, and how each member is seen by dispatch now. */
export function useExecutorGroupCapacity(groupId: ExecutorGroupId, enabled = true) {
  return useQuery<ExecutorGroupCapacity>(executorGroupCapacityQueryOptions(groupId, enabled));
}

export function executorRoutingRulesQueryOptions() {
  return {
    queryKey: executorRoutingRulesKey(),
    queryFn: async () => (await listExecutorRoutingRules({})).data,
    refetchOnWindowFocus: 'always',
    staleTime: 0,
  } as const;
}

/** The current rule of each work kind that has one, and the routing mode. */
export function useExecutorRoutingRules() {
  return useQuery<ExecutorRoutingRuleList>(executorRoutingRulesQueryOptions());
}

export function executorRoutingPreviewQueryOptions(enabled: boolean) {
  return {
    queryKey: executorRoutingPreviewKey(),
    queryFn: async () => (await previewExecutorRouting({})).data,
    refetchOnWindowFocus: false,
    refetchOnMount: 'always',
    staleTime: 0,
    gcTime: 0,
    enabled,
  } as const;
}

/** The proposed cut-over, read only while `enabled` (the panel is open). Writes nothing. */
export function useExecutorRoutingPreview(enabled: boolean) {
  return useQuery<ExecutorRoutingPreview>(executorRoutingPreviewQueryOptions(enabled));
}
