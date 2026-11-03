'use client';

/**
 * The commands on a connection (`EXEC-HTTP-01`): create, revise, archive, probe and generate
 * an SSH key, and (`EXEC-PULL-01`) issue and revoke a runner token. Each takes the idempotency
 * key its caller minted for the intent and reuses it on an explicit repeat; `retry: false`, so
 * nothing here repeats a write on its own.
 *
 * Every command invalidates `execution.all()`: a connection's list row, its detail (revisions
 * and probes) and the route's choices all answer from what a command changes. None of them
 * changes a number the dashboard reads.
 *
 * `EXEC2-WEB-WIZARD-01` adds the four commands of the universal agent (ADR-0026 decisions 4, 7
 * and 8): issue an enrollment, start an install over SSH, confirm the observed host key, and set
 * or clear the administrator's integration mark. They live here, beside the commands they
 * resemble, because the dashboard-invalidation guard maps this file as one mutation hook. The
 * install session's read is filed under `execution`, so each of them refreshes it too.
 *
 * **There is no hook for `setExecutorSecret`, on purpose.** A key set through a hook would be a
 * JavaScript value. The key is typed into `features/set-executor-secret`'s server-rendered
 * form and reaches the API through the BFF's `executor-secret` door.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type {
  CreateExecutorAgentInstallRequest,
  ExecutorAgentInstall,
  ExecutorAgentInstallId,
  ExecutorConnection,
  ExecutorConnectionId,
  ExecutorKind,
  ExecutorProbe,
  ExecutorRevision,
  ExecutorRunnerTokenId,
  ExecutorSshKey,
  IssuedExecutorEnrollment,
  IssuedRunnerToken,
  ReviseExecutorConnectionRequest,
  RunnerTokenMetadata,
} from '@/shared/api';
import {
  archiveExecutorConnection,
  confirmExecutorAgentInstallHostKey,
  createExecutorAgentInstall,
  createExecutorConnection,
  generateExecutorSshKey,
  issueExecutorEnrollment,
  issueRunnerToken,
  queryKeys,
  requestExecutorProbe,
  reviseExecutorConnection,
  revokeRunnerToken,
  setExecutorIntegrationAuthorisation,
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

/**
 * «Выпустить токен» (`issueRunnerToken`, `EXEC-PULL-01`). The answer carries the token's value,
 * which the stand shows **once**. The mutation keeps no copy (`gcTime: 0`): the screen takes the
 * value from `mutateAsync`, holds it in its own state for one reading and drops it.
 */
export function useIssueRunnerToken() {
  const refresh = useRefreshExecution();
  return useMutation<
    IssuedRunnerToken,
    unknown,
    { connectionId: ExecutorConnectionId; expiresInDays: number; idempotencyKey: string }
  >({
    mutationFn: async ({ connectionId, expiresInDays, idempotencyKey }) =>
      (await issueRunnerToken({
        path: { connection_id: connectionId },
        body: { expires_in_days: expiresInDays },
        idempotencyKey,
      })).data,
    retry: false,
    gcTime: 0,
    onSuccess: refresh,
  });
}

/** «Отозвать» (`revokeRunnerToken`): the runner's next call is refused. */
export function useRevokeRunnerToken() {
  const refresh = useRefreshExecution();
  return useMutation<
    RunnerTokenMetadata,
    unknown,
    { connectionId: ExecutorConnectionId; tokenId: ExecutorRunnerTokenId; idempotencyKey: string }
  >({
    mutationFn: async ({ connectionId, tokenId, idempotencyKey }) =>
      (await revokeRunnerToken({
        path: { connection_id: connectionId, token_id: tokenId },
        idempotencyKey,
      })).data,
    retry: false,
    onSuccess: refresh,
  });
}

/**
 * «Новая команда» / «Получить команду» (`issueExecutorEnrollment`, `EXEC2-WEB-WIZARD-01`, ADR-0026
 * decision 4). The answer carries the grant's secret inside the copyable command, which the stand
 * shows **once**; the mutation keeps no copy (`gcTime: 0`) and the screen drops the value when its
 * box is closed.
 *
 * **Every press is a new intent.** A repeat of the same Idempotency-Key is answered
 * `conflict` / `enrollment_shown_once` — the secret was not stored and cannot be shown again — so
 * the caller releases its key whatever the outcome and a repeat after an unknown outcome is a new
 * grant, which revokes the previous unredeemed one.
 */
export function useIssueExecutorEnrollment() {
  const refresh = useRefreshExecution();
  return useMutation<
    IssuedExecutorEnrollment,
    unknown,
    { connectionId: ExecutorConnectionId; idempotencyKey: string }
  >({
    mutationFn: async ({ connectionId, idempotencyKey }) =>
      (await issueExecutorEnrollment({ path: { connection_id: connectionId }, idempotencyKey })).data,
    retry: false,
    gcTime: 0,
    onSuccess: refresh,
  });
}

/**
 * «Начать установку» (`createExecutorAgentInstall`, path A, ADR-0026 decision 7). The wizard builds
 * the body from a host, a port and a user and always asks for the key the stand makes
 * (`generated_key`); no secret is part of the request, so none is kept or cleared here. The answer
 * carries the public half and the `authorized_keys` line the administrator adds to the host.
 */
export function useCreateExecutorAgentInstall() {
  const refresh = useRefreshExecution();
  return useMutation<
    ExecutorAgentInstall,
    unknown,
    { connectionId: ExecutorConnectionId; body: CreateExecutorAgentInstallRequest; idempotencyKey: string }
  >({
    mutationFn: async ({ connectionId, body, idempotencyKey }) =>
      (await createExecutorAgentInstall({ path: { connection_id: connectionId }, body, idempotencyKey })).data,
    retry: false,
    onSuccess: refresh,
  });
}

/**
 * «Подтверждаю отпечаток» (`confirmExecutorAgentInstallHostKey`): the fingerprint the worker
 * observed, sent back by value. There is no trust on first use; the stand refuses a fingerprint
 * that is not the observed one.
 */
export function useConfirmExecutorAgentInstallHostKey() {
  const refresh = useRefreshExecution();
  return useMutation<
    ExecutorAgentInstall,
    unknown,
    {
      connectionId: ExecutorConnectionId;
      installId: ExecutorAgentInstallId;
      hostKeyFingerprint: string;
      idempotencyKey: string;
    }
  >({
    mutationFn: async ({ connectionId, installId, hostKeyFingerprint, idempotencyKey }) =>
      (await confirmExecutorAgentInstallHostKey({
        path: { connection_id: connectionId, install_id: installId },
        body: { host_key_fingerprint: hostKeyFingerprint },
        idempotencyKey,
      })).data,
    retry: false,
    onSuccess: refresh,
  });
}

/**
 * The administrator's mark «разрешено для интеграции» (`setExecutorIntegrationAuthorisation`,
 * `R-149b`, ADR-0026 decision 8). It is one of four distinct statuses and implies none of the
 * others; setting an already set mark or clearing an absent one answers the connection as it is.
 */
export function useSetExecutorIntegrationAuthorisation() {
  const refresh = useRefreshExecution();
  return useMutation<
    ExecutorConnection,
    unknown,
    { connectionId: ExecutorConnectionId; authorised: boolean; idempotencyKey: string }
  >({
    mutationFn: async ({ connectionId, authorised, idempotencyKey }) =>
      (await setExecutorIntegrationAuthorisation({
        path: { connection_id: connectionId },
        body: { authorised },
        idempotencyKey,
      })).data,
    retry: false,
    onSuccess: refresh,
  });
}
