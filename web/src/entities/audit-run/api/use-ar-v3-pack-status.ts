'use client';

/**
 * `getArV3BetaPackStatus` — whether a reviewed AR v3 beta pack is installed, read on mount.
 *
 * One query, two readers: the settings panel that explains the state and the version's run
 * list that offers the six-check start only on an installed pack. They share the key
 * (`queryKeys.runs.arV3PackStatus`), so they cannot disagree about what the server said.
 *
 * The answer is returned as a **view**, never as the raw body: `loading`, `error`, or a
 * `read` carrying `readArV3PackStatus`'s classification (installed, not installed, or a
 * fault). A reader that wanted the body would be one that could mistake a malformed answer
 * for an installed pack, and a failed re-read — which React Query reports as an error while
 * still holding the earlier body — for a current one.
 *
 * The application's default freshness applies: the pack changes only when the server is
 * redeployed with another manifest, and a reload or the panel's retry re-reads it.
 */

import { useQuery } from '@tanstack/react-query';

import type { ArV3BetaPackStatus } from '@/shared/api';
import { getArV3BetaPackStatus, queryKeys } from '@/shared/api';

import type { ArV3PackReading } from '../model/ar-v3-pack-status';
import { readArV3PackStatus } from '../model/ar-v3-pack-status';

export type ArV3PackView =
  | { readonly phase: 'loading' }
  | { readonly phase: 'error'; readonly error: unknown }
  | { readonly phase: 'read'; readonly reading: ArV3PackReading };

export function arV3PackStatusQueryOptions() {
  return {
    queryKey: queryKeys.runs.arV3PackStatus(),
    queryFn: async (): Promise<ArV3BetaPackStatus> => (await getArV3BetaPackStatus({})).data,
  } as const;
}

export function useArV3PackStatus(): { readonly view: ArV3PackView; readonly refetch: () => void } {
  const query = useQuery<ArV3BetaPackStatus>(arV3PackStatusQueryOptions());
  const view: ArV3PackView = query.isError
    ? { phase: 'error', error: query.error }
    : query.isSuccess
      ? { phase: 'read', reading: readArV3PackStatus(query.data) }
      : { phase: 'loading' };
  return { view, refetch: () => void query.refetch() };
}
