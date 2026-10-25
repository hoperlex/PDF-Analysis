'use client';

/**
 * What of one six-check start must outlive the control that sends it.
 *
 * The control is drawn only while the reviewed pack reads as installed, so a status re-read
 * that fails takes it off the page — and everything it held with it: the mutation observer
 * whose per-call `onSuccess` opens the started group, and the idempotency key in its `useRef`.
 * A request already on its way would then complete unseen, and the control coming back would
 * mint a new key, so the next press could make a second group of six runs (the server dedupes
 * by key alone).
 *
 * The caller that decides whether to draw the control holds this instead, and passes it down:
 *
 *   `idempotencyKey`  held by the caller, so it is the same for as long as the caller lives and
 *                     the version is the same — whether or not the control is mounted;
 *   `inFlight`        read from the mutation cache, which keeps a mutation until it settles
 *                     whether or not anything is observing it, so the caller can keep the
 *                     control mounted exactly while a request for this version is pending.
 *
 * The key is still one per intent (`useIntentKey`): a changed version is a different intent
 * and mints a new one. It is not kept beyond the caller's life; a page left and opened again
 * is a new intent.
 */

import { useIsMutating } from '@tanstack/react-query';

import type { VersionUid } from '@/shared/api';
import { useIntentKey } from '@/shared/lib';

import type { StartArV3GroupCommand } from './use-start-ar-v3-group';
import { START_AR_V3_GROUP_MUTATION_KEY } from './use-start-ar-v3-group';

export interface ArV3GroupStartIntent {
  /** The caller's key for starting this version's six checks; the same on every retry. */
  readonly idempotencyKey: string;
  /** A start for this version has been sent and not yet answered. */
  readonly inFlight: boolean;
}

export function useArV3GroupStartIntent(versionUid: VersionUid): ArV3GroupStartIntent {
  const idempotencyKey = useIntentKey(`start-ar-v3-group:${versionUid}`);
  const pending = useIsMutating({
    mutationKey: START_AR_V3_GROUP_MUTATION_KEY,
    predicate: (mutation) =>
      (mutation.state.variables as StartArV3GroupCommand | undefined)?.versionUid === versionUid,
  });
  return { idempotencyKey, inFlight: pending > 0 };
}
