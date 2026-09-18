/**
 * One idempotency key per intent, reused on every retry.
 *
 * `web/docs/PC01_UI_SEAM.md` §4.3: mint the key when the user expresses the intent, and
 * keep it for the lifetime of that intent **including every retry**. A fresh key is a
 * second command, so a retry that mints one turns "my accept failed, try again" into two
 * accepts in the ledger — and the ledger is append-only, so there is nothing to undo.
 *
 * The rule needs somewhere to live that is not a component, because a component that keeps
 * the key in a `useState` loses it on remount. Since `D-22` it lives in
 * `shared/lib/intent-key`, once, as a pure function over an opaque signature. What stays
 * here is the part that is genuinely about decisions: **what makes two decision intents
 * the same**.
 *
 * What makes two intents "the same": the event type, the observation being judged and the
 * comment text. Pressing Accept, having it fail, and pressing Accept again is one intent.
 * Pressing Accept and then Reject is two. Typing a different comment is two.
 */

import type { AppendDecisionRequest } from '@/shared/api';
import type { IntentRecord } from '@/shared/lib';
import { resolveIntentKey as resolveBySignature } from '@/shared/lib';

/**
 * The key currently held for an intent, and the intent it belongs to.
 *
 * Re-exported from `shared/lib` rather than redeclared: `D-22` is about one rule living
 * in one place, and two structurally identical records are two places.
 */
export type { IntentRecord };

/**
 * A stable, collision-resistant signature for one decision intent.
 *
 * The parts are length-prefixed rather than joined by a separator, because a comment
 * containing the separator would otherwise let two different intents produce one
 * signature — and the consequence of that collision is a suppressed second command.
 */
export function intentSignature(request: AppendDecisionRequest): string {
  const comment = request.comment ?? '';
  return [
    request.event_type,
    request.finding_observation_id,
    `${[...comment].length}:${comment}`,
  ]
    .map((part) => `${part.length}|${part}`)
    .join('');
}

/**
 * Return the key to send for this request: the one already held when the intent is
 * unchanged, a freshly minted one when it is not.
 *
 * `mint` is injected so a test can assert *when* a key is minted rather than only what it
 * looks like. Production passes `newIdempotencyKey` from the transport seam.
 */
export function resolveIntentKey(
  previous: IntentRecord | null,
  request: AppendDecisionRequest,
  mint: () => string,
): IntentRecord {
  return resolveBySignature(previous, intentSignature(request), mint);
}
