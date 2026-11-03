'use client';

/**
 * The administrator's commands on groups, rules and the routing mode (`EXEC2-WEB-GROUPS-01`,
 * ADR-0026 decisions 10, 11 and 17): create a group, revise it, archive it, point the rule of a
 * work kind at a group revision, and change the mode (the cut-over and its rollback).
 *
 * Each takes the idempotency key its caller minted for the intent and reuses it on an explicit
 * repeat; `retry: false`, so nothing here repeats a write on its own. Every command invalidates
 * the `execution` root: the groups, a group's capacity, the rules with the mode, the proposal and
 * the connections' `routed_work_kinds` all answer from what a command changes. None of them
 * changes a number the dashboard reads, so none invalidates it
 * (`tests/guards/dashboard-invalidation.guard.test.ts` maps this file as `false`). The server
 * checks the role again on every write.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type {
  CreateExecutorGroupRequest,
  ExecutorGroup,
  ExecutorGroupId,
  ExecutorGroupRevisionId,
  ExecutorRoutingModeResult,
  ExecutorRoutingRule,
  ExecutorWorkKind,
  ReviseExecutorGroupRequest,
  SetExecutorRoutingModeRequest,
} from '@/shared/api';
import {
  archiveExecutorGroup,
  createExecutorGroup,
  queryKeys,
  reviseExecutorGroup,
  setExecutorRoutingMode,
  setExecutorRoutingRule,
} from '@/shared/api';

function useRefreshExecution() {
  const client = useQueryClient();
  return () => {
    void client.invalidateQueries({ queryKey: queryKeys.execution.all() });
  };
}

export function useCreateExecutorGroup() {
  const refresh = useRefreshExecution();
  return useMutation<ExecutorGroup, unknown, { body: CreateExecutorGroupRequest; idempotencyKey: string }>({
    mutationFn: async ({ body, idempotencyKey }) => (await createExecutorGroup({ body, idempotencyKey })).data,
    retry: false,
    onSuccess: refresh,
  });
}

export function useReviseExecutorGroup() {
  const refresh = useRefreshExecution();
  return useMutation<
    ExecutorGroup,
    unknown,
    { groupId: ExecutorGroupId; body: ReviseExecutorGroupRequest; idempotencyKey: string }
  >({
    mutationFn: async ({ groupId, body, idempotencyKey }) =>
      (await reviseExecutorGroup({ path: { group_id: groupId }, body, idempotencyKey })).data,
    retry: false,
    onSuccess: refresh,
  });
}

export function useArchiveExecutorGroup() {
  const refresh = useRefreshExecution();
  return useMutation<ExecutorGroup, unknown, { groupId: ExecutorGroupId; idempotencyKey: string }>({
    mutationFn: async ({ groupId, idempotencyKey }) =>
      (await archiveExecutorGroup({ path: { group_id: groupId }, idempotencyKey })).data,
    retry: false,
    onSuccess: refresh,
  });
}

export function useSetExecutorRoutingRule() {
  const refresh = useRefreshExecution();
  return useMutation<
    ExecutorRoutingRule,
    unknown,
    { workKind: ExecutorWorkKind; groupRevisionId: ExecutorGroupRevisionId; idempotencyKey: string }
  >({
    mutationFn: async ({ workKind, groupRevisionId, idempotencyKey }) =>
      (await setExecutorRoutingRule({
        path: { work_kind: workKind },
        body: { group_revision_id: groupRevisionId },
        idempotencyKey,
      })).data,
    retry: false,
    onSuccess: refresh,
  });
}

export function useSetExecutorRoutingMode() {
  const refresh = useRefreshExecution();
  return useMutation<
    ExecutorRoutingModeResult,
    unknown,
    { body: SetExecutorRoutingModeRequest; idempotencyKey: string }
  >({
    mutationFn: async ({ body, idempotencyKey }) => (await setExecutorRoutingMode({ body, idempotencyKey })).data,
    retry: false,
    onSuccess: refresh,
  });
}
