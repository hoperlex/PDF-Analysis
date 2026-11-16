'use client';

/**
 * `setMyLastProject` (`UIP-G-06`, owner ruling Г7-B): the account's own choice of an object, kept on the server, so that the
 * screens that follow the object open on it when their address names none.
 *
 * It is called for the choice of one object, in the selector of the header and in a screen's own list of objects. The
 * all-objects view is never sent (the operation has no body for it): that choice lives in the address (`?project=all`).
 *
 * **A refusal never stops the choice.** The address is already the chosen object's and the screen shows it; the command only
 * makes the choice outlive the address. So a failure is not thrown at the caller: it is returned as `failure`, a Russian
 * sentence the caller must show (no silent fallback), and it stays until the next choice or {@link RememberProject.reset}.
 *
 * **One key per choice**: `newIdempotencyKey` is minted once per call, and nothing repeats a choice on its own
 * (`retry: false`). A second choice is a second command with a key of its own.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { Account } from '@/shared/api';
import { failureMessage, newIdempotencyKey, queryKeys, setMyLastProject } from '@/shared/api';

/** What a screen shows when the choice could not be kept. */
export interface RememberProjectFailure {
  /** The Russian sentence; never a thrown value's own message. */
  readonly detail: string;
  readonly correlationId: string | null;
}

export interface RememberProject {
  /** Asks the server to keep `projectUid` as the account's last object. Does not wait and does not throw. */
  readonly remember: (projectUid: string) => void;
  /** The last choice that could not be kept, or `null`. */
  readonly failure: RememberProjectFailure | null;
  /** Forgets `failure`. */
  readonly reset: () => void;
}

export function useRememberProject(): RememberProject {
  const client = useQueryClient();
  const mutation = useMutation<void, unknown, { readonly projectUid: string; readonly idempotencyKey: string }>({
    mutationFn: async ({ projectUid, idempotencyKey }) => {
      await setMyLastProject({ body: { project_uid: projectUid }, idempotencyKey });
    },
    retry: false,
    onSuccess: (_none, { projectUid }) => {
      // The stored choice is known at once: it is written to the account's answer, and the read then refreshes behind it.
      client.setQueryData<Account>(queryKeys.account.me(), (me) => (me === undefined ? me : { ...me, last_project_uid: projectUid }));
      void client.invalidateQueries({ queryKey: queryKeys.account.me() });
    },
  });
  const { mutate, reset } = mutation;
  const refusal = mutation.isError ? failureMessage(mutation.error) : null;
  return {
    remember: (projectUid) => mutate({ projectUid, idempotencyKey: newIdempotencyKey() }),
    failure: refusal === null ? null : { detail: refusal.detail, correlationId: refusal.correlationId },
    reset,
  };
}
