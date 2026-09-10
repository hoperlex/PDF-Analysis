'use client';

/**
 * One idempotency key per intent, held for the lifetime of that intent.
 *
 * The contract's rule, restated: a key is minted when the user expresses an intent and
 * reused on **every** retry of it. Minting a fresh key on retry is a second command, and
 * a second command is a second project, version or run.
 *
 * The intent is identified by its payload signature. While the signature is unchanged
 * the key is unchanged, so every retry replays the same command; when the user edits the
 * payload the intent is a different one and a new key is minted, which is what keeps a
 * changed payload from arriving under an old key as `idempotency_key_reuse`.
 *
 * This hook is duplicated in each of the three write features. It belongs in
 * `shared/lib`, which a Gate B session may not write to — see the session report.
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
