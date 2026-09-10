'use client';

/**
 * The start-run command.
 *
 * **`provider_mode` is not sent.** The contract makes it optional and defaults it to the
 * server's configured mode, and it notes that a client asking for `live` is asking to
 * spend money against the `OD-03` ceiling. A screen that offered the choice would also
 * be the screen that offers to retry a failed live run as a recorded one, which is
 * exactly the substitution that makes a replayed run look like evidence of a real
 * provider call. The mode this run actually used is read back from the reading and shown.
 *
 * The 202 body is a full `RunStatus`, so it seeds `queryKeys.runs.detail(run_id)`: the
 * run screen opens on the run's real first state instead of on a loading state for a
 * reading it was already handed.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { RunStatus, VersionUid } from '@/shared/api';
import { queryKeys, startRun } from '@/shared/api';

export interface StartRunCommand {
  readonly versionUid: VersionUid;
  /** Minted once per intent by the caller and reused on every retry. */
  readonly idempotencyKey: string;
}

export function useStartRun() {
  const queryClient = useQueryClient();

  return useMutation<RunStatus, unknown, StartRunCommand>({
    mutationFn: async ({ versionUid, idempotencyKey }) => {
      const response = await startRun({ body: { version_uid: versionUid }, idempotencyKey });
      return response.data;
    },
    onSuccess: (run) => {
      queryClient.setQueryData(queryKeys.runs.detail(run.run_id), run);
    },
  });
}
