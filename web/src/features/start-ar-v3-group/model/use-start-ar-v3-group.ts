'use client';

/**
 * The start-six-checks command (`startArV3BetaGroup`).
 *
 * **`provider_mode` is not sent**, as `useStartRun` does not send it: the request carries the
 * version and nothing else, the server picks the mode it is configured for and the pack it has
 * installed, and a screen that offered either would offer to spend money or to pick evidence
 * the reviewer cannot judge from here. The 202 body is the group (`ArV3BetaGroup`); the six
 * Runs in it are read back through the group review, not seeded into the single-run caches.
 *
 * Six queued Runs are a change to everything a single accepted run changes, so the same reads
 * are invalidated: the version's run lists (all of `runs`), the dashboard's one read
 * (`run_activity.by_state` moves the moment the command is accepted) and the execution queue
 * and journal (six new queued jobs). `tests/guards/dashboard-invalidation.guard.test.ts` holds
 * the dashboard half.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { ArV3BetaGroup, VersionUid } from '@/shared/api';
import { queryKeys, startArV3BetaGroup } from '@/shared/api';

/**
 * The mutation's key, so a caller can ask the cache whether a start is pending
 * (`useArV3GroupStartIntent`) without owning the mutation.
 */
export const START_AR_V3_GROUP_MUTATION_KEY = ['start-ar-v3-group'] as const;

export interface StartArV3GroupCommand {
  readonly versionUid: VersionUid;
  /** Minted once per intent by the caller and reused on every retry. */
  readonly idempotencyKey: string;
  readonly relaxedLimits?: boolean | undefined;
}

export function useStartArV3Group() {
  const queryClient = useQueryClient();

  return useMutation<ArV3BetaGroup, unknown, StartArV3GroupCommand>({
    mutationKey: START_AR_V3_GROUP_MUTATION_KEY,
    mutationFn: async ({ versionUid, idempotencyKey, relaxedLimits }) => {
      const response = await startArV3BetaGroup({
        body: { version_uid: versionUid, ...(relaxedLimits ? { relaxed_limits: true } : {}) },
        idempotencyKey,
      });
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.runs.all() });
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.summary() });
      void queryClient.invalidateQueries({ queryKey: queryKeys.execution.all() });
    },
  });
}
