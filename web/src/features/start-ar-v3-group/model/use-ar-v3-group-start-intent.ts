'use client';

/**
 * What of one six-check start must outlive the control that sends it.
 *
 * The control is drawn only while the reviewed pack reads as installed or a start is pending, and
 * the list around it can stop showing it too (its page is loading, its read failed). A control
 * taken off the page takes with it everything it held: the mutation observer whose per-call
 * `onSuccess` opens the started group (TanStack drops that callback with the observer, so a 202
 * that arrives while no control is mounted would open nothing), the refusal a failed start left,
 * and the idempotency key in its `useRef`. The control coming back would mint a new key, and the
 * next press could make a second group of six runs (the server dedupes by key alone).
 *
 * The caller that decides whether to draw the control, and that is itself mounted for as long as
 * the version's list is, holds this instead and passes it down:
 *
 *   `idempotencyKey`  the same for as long as the caller lives and the version is the same,
 *                     whether or not the control is mounted;
 *   `mutation`        the start's observer, so a per-call `onSuccess` outlives the control that
 *                     sent it and a refusal waits for the control to come back;
 *   `inFlight`        a start for this version is pending, read from the mutation cache (which
 *                     keeps a mutation until it settles whether or not anything observes it) so
 *                     the caller can keep the control drawn exactly while a request is on its way.
 *
 * The key is still one per intent (`useIntentKey`): a changed version is a different intent and
 * mints a new one. It is not kept beyond the caller's life; a page left and opened again is a new
 * intent. A caller that can see its version change while mounted keys itself by the version
 * (`RunList` does): the observer holds one version's answer.
 */

import { useQueryClient } from '@tanstack/react-query';
import type { UseMutationResult } from '@tanstack/react-query';
import { useCallback, useState, useSyncExternalStore } from 'react';

import type { ArV3BetaGroup, VersionUid } from '@/shared/api';
import { useIntentKey } from '@/shared/lib';

import type { StartArV3GroupCommand } from './use-start-ar-v3-group';
import { START_AR_V3_GROUP_MUTATION_KEY, useStartArV3Group } from './use-start-ar-v3-group';

export interface ArV3GroupStartIntent {
  /** The caller's key for starting this version's six checks; the same on every retry. */
  readonly idempotencyKey: string;
  /** A start for this version has been sent and not yet answered. */
  readonly inFlight: boolean;
  /** The start's observer, held by the caller; the control sends through it and reads it. */
  readonly mutation: UseMutationResult<ArV3BetaGroup, unknown, StartArV3GroupCommand>;
  readonly relaxedLimits: boolean;
  readonly setRelaxedLimits: (value: boolean) => void;
}

/**
 * Whether a start for `versionUid` is pending, recomputed from the mutation cache on every render
 * and on every cache event. `useIsMutating` computes its answer on a cache event only, so a
 * changed `versionUid` kept the previous version's answer until the next event.
 */
function useStartPending(versionUid: VersionUid): boolean {
  const cache = useQueryClient().getMutationCache();
  const subscribe = useCallback((notify: () => void) => cache.subscribe(() => notify()), [cache]);
  return useSyncExternalStore(
    subscribe,
    () =>
      cache.findAll({
        mutationKey: START_AR_V3_GROUP_MUTATION_KEY,
        status: 'pending',
        predicate: (mutation) =>
          (mutation.state.variables as StartArV3GroupCommand | undefined)?.versionUid === versionUid,
      }).length > 0,
    () => false,
  );
}

export function useArV3GroupStartIntent(versionUid: VersionUid): ArV3GroupStartIntent {
  const [relaxedLimits, setRelaxedLimits] = useState(false);
  const idempotencyKey = useIntentKey(`start-ar-v3-group:${versionUid}:${relaxedLimits ? 'relaxed' : 'standard'}`);
  const mutation = useStartArV3Group();
  const inFlight = useStartPending(versionUid);
  return {
    idempotencyKey,
    inFlight,
    mutation,
    relaxedLimits,
    setRelaxedLimits: (value) => {
      if (inFlight || mutation.isPending) return;
      mutation.reset();
      setRelaxedLimits(value);
    },
  };
}
