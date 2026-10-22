'use client';

/**
 * `setExecutorRoute` (`EXEC-HTTP-01`): an administrator names the connection that serves a
 * kind of model work, and optionally a standby. The standby is used only at run start, and
 * only when the primary has no `ok` probe on its current secret or is archived; every use is
 * journaled and nothing falls back implicitly.
 *
 * The caller mints the key once per intent and passes the same one on an explicit repeat;
 * `retry: false`. A route changes what the connections' rows answer (`routed_work_kinds`), so
 * the whole `execution` root is invalidated. No number the dashboard reads changes.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { ExecutorConnectionId, ExecutorRoute, ExecutorWorkKind } from '@/shared/api';
import { queryKeys, setExecutorRoute } from '@/shared/api';

export function useSetExecutorRoute() {
  const client = useQueryClient();
  return useMutation<
    ExecutorRoute,
    unknown,
    {
      workKind: ExecutorWorkKind;
      primary: ExecutorConnectionId;
      standby: ExecutorConnectionId | null;
      idempotencyKey: string;
    }
  >({
    mutationFn: async ({ workKind, primary, standby, idempotencyKey }) =>
      (
        await setExecutorRoute({
          body: {
            work_kind: workKind,
            primary_connection_id: primary,
            ...(standby === null ? {} : { standby_connection_id: standby }),
          },
          idempotencyKey,
        })
      ).data,
    retry: false,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.execution.all() });
    },
  });
}
