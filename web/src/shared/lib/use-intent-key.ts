'use client';

/**
 * The hook the three write features call: `create-project`, `upload-document` and
 * `start-run`. Before `D-22` each of them held its own byte-identical copy, and each copy
 * carried a comment saying it belonged here and that a Gate B session could not put it
 * here. It is here now, once, and it contains **no copy of the rule** — the rule is
 * `resolveIntentKey`, beside it, pure and injectable.
 *
 * A `useRef` and not a `useState`: the key must be stable within a render pass, and
 * setting state during render to keep it would be a second mechanism for the same fact.
 */

import { useRef } from 'react';

import { newIdempotencyKey } from '@/shared/api';

import type { IntentRecord } from './intent-key';
import { resolveIntentKey } from './intent-key';

/** The idempotency key for the current intent, stable until `signature` changes. */
export function useIntentKey(signature: string): string {
  const held = useRef<IntentRecord | null>(null);
  held.current = resolveIntentKey(held.current, signature, newIdempotencyKey);
  return held.current.idempotencyKey;
}
