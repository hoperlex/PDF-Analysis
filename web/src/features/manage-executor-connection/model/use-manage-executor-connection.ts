'use client';

/**
 * The commands on a connection (`EXEC-HTTP-01`): create, revise, archive, probe and generate
 * an SSH key. Each takes the idempotency key its caller minted for the intent and reuses it on
 * an explicit repeat; `retry: false`, so nothing here repeats a write on its own.
 *
 * Every command invalidates `execution.all()`: a connection's list row, its detail (revisions
 * and probes) and the route's choices all answer from what a command changes. None of them
 * changes a number the dashboard reads.
 *
 * **There is no hook for `setExecutorSecret`, on purpose.** A key set through a hook would be a
 * JavaScript value. The key is typed into `features/set-executor-secret`'s server-rendered
 * form and reaches the API through the BFF's `executor-secret` door.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type {
  ExecutorConnection,
  ExecutorConnectionId,
  ExecutorKind,
  ExecutorProbe,
  ExecutorRevision,
  ExecutorSshKey,
  ReviseExecutorConnectionRequest,
} from '@/shared/api';
import {
  archiveExecutorConnection,
  createExecutorConnection,
  generateExecutorSshKey,
  queryKeys,
  requestExecutorProbe,
  reviseExecutorConnection,
} from '@/shared/api';

function useRefreshExecution() {
  const client = useQueryClient();
  return () => {
    void client.invalidateQueries({ queryKey: queryKeys.execution.all() });
  };
}

export function useCreateExecutorConnection() {
  const refresh = useRefreshExecution();
  return useMutation<
    ExecutorConnection,
    unknown,
    { kind: ExecutorKind; displayName: string; idempotencyKey: string }
  >({
    mutationFn: async ({ kind, displayName, idempotencyKey }) =>
      (await createExecutorConnection({ body: { kind, display_name: displayName }, idempotencyKey })).data,
    retry: false,
    onSuccess: refresh,
  });
}

export function useReviseExecutorConnection() {
  const refresh = useRefreshExecution();
  return useMutation<
    ExecutorRevision,
    unknown,
    { connectionId: ExecutorConnectionId; body: ReviseExecutorConnectionRequest; idempotencyKey: string }
  >({
    mutationFn: async ({ connectionId, body, idempotencyKey }) =>
      (await reviseExecutorConnection({ path: { connection_id: connectionId }, body, idempotencyKey })).data,
    retry: false,
    onSuccess: refresh,
  });
}

export function useArchiveExecutorConnection() {
  const refresh = useRefreshExecution();
  return useMutation<
    ExecutorConnection,
    unknown,
    { connectionId: ExecutorConnectionId; idempotencyKey: string }
  >({
    mutationFn: async ({ connectionId, idempotencyKey }) =>
      (await archiveExecutorConnection({ path: { connection_id: connectionId }, idempotencyKey })).data,
    retry: false,
    onSuccess: refresh,
  });
}

export function useRequestExecutorProbe() {
  const refresh = useRefreshExecution();
  return useMutation<
    ExecutorProbe,
    unknown,
    { connectionId: ExecutorConnectionId; idempotencyKey: string }
  >({
    mutationFn: async ({ connectionId, idempotencyKey }) =>
      (await requestExecutorProbe({ path: { connection_id: connectionId }, idempotencyKey })).data,
    retry: false,
    onSuccess: refresh,
  });
}

export function useGenerateExecutorSshKey() {
  const refresh = useRefreshExecution();
  return useMutation<
    ExecutorSshKey,
    unknown,
    { connectionId: ExecutorConnectionId; idempotencyKey: string }
  >({
    mutationFn: async ({ connectionId, idempotencyKey }) =>
      (await generateExecutorSshKey({ path: { connection_id: connectionId }, idempotencyKey })).data,
    retry: false,
    onSuccess: refresh,
  });
}
