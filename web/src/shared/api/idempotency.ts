/**
 * Idempotency keys.
 *
 * The contract scopes a command key to command type plus target aggregate, and
 * `P02_SEAMS.md` section 9.5 records that PC-01's uniqueness is `(command_type,
 * idempotency_key)` because there is no authenticated subject yet. Two rules follow for
 * the client and both matter more than the generator does:
 *
 *   - **One key per intent.** Mint the key when the user expresses the intent — presses
 *     "create", chooses a file, clicks "accept" — and keep it for the lifetime of that
 *     intent, including every retry.
 *   - **Never re-mint on retry.** `idempotency_key_in_progress` is resolved by retrying
 *     the *same* key. A fresh key is a second command, and the server is right to treat
 *     it as one.
 *
 * `idempotency_key_reuse` — the same key with a different payload — is a terminal,
 * user-visible conflict. It is never resolved by minting a new key either: the payload
 * changed, so the user is doing something new and should say so.
 */

import type { IdempotencyKey } from './generated/types.gen';

const KEY_PREFIX = 'ik_';

/**
 * Mint one key. The result matches the contract's `IdempotencyKey` pattern
 * `^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$`.
 *
 * Call this once per intent, never inside a retry loop.
 */
export function newIdempotencyKey(): IdempotencyKey {
  const uuid = globalThis.crypto?.randomUUID?.();
  if (typeof uuid === 'string') return `${KEY_PREFIX}${uuid}`;

  // A runtime with no Web Crypto. Still opaque, still unique enough for one intent.
  const random = Math.random().toString(36).slice(2, 14).padEnd(12, '0');
  return `${KEY_PREFIX}${Date.now().toString(36)}-${random}`;
}
