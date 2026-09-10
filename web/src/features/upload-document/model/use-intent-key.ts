'use client';

/**
 * One idempotency key per upload intent, held for the lifetime of that intent.
 *
 * The intent is "upload this file to this project". Retrying after a dependency outage
 * must reuse the key, or the retry publishes a second version of the same document. The
 * signature therefore covers the chosen file and the title typed beside it: change
 * either and it is a different upload, with a different key.
 *
 * Duplicated from the other two write features. It belongs in `shared/lib`, which a
 * Gate B session may not write to — see the session report.
 */

import { useRef } from 'react';

import { newIdempotencyKey } from '@/shared/api';

/** The key for the current intent, stable until `signature` changes. */
export function useIntentKey(signature: string): string {
  const held = useRef<{ signature: string; key: string } | null>(null);
  if (held.current === null || held.current.signature !== signature) {
    held.current = { signature, key: newIdempotencyKey() };
  }
  return held.current.key;
}
