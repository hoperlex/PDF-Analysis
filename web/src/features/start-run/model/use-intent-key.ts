'use client';

/**
 * One idempotency key per run intent, held for the lifetime of that intent.
 *
 * The contract is explicit about what the two halves mean here: the same key with the
 * same payload returns the existing run and creates nothing, whatever state that run is
 * in, terminal included; a new key over a terminal run creates a new run and leaves the
 * terminal one exactly as it was. So a retry after `dependency_unavailable` must carry
 * the same key — a fresh one would be a second run against the same version.
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
