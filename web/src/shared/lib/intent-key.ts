/**
 * One idempotency key per intent, held for the lifetime of that intent — **once**.
 *
 * `DEBT_REGISTER.md` **D-22**: this rule existed four times. Once as a pure function,
 * `resolveIntentKey` in `entities/expert-decision`, over an `AppendDecisionRequest`; and
 * three times as a hand-copied `useIntentKey` hook in `create-project`,
 * `upload-document` and `start-run`, each carrying a comment saying it belonged in
 * `shared/lib` and that a Gate B session could not put it there. `W16-WEB` measured the
 * consequence: mutations U-06, U-07 and U-08 survive *by construction*, because the rule
 * inside a `useRef` that is always fresh on a single render pass cannot be made to
 * misbehave observably. The rule is here now, as a pure function, so it can.
 *
 * The rule itself, from `web/docs/PC01_UI_SEAM.md` §4.3: mint the key when the user
 * expresses the intent, and reuse it on **every** retry of that intent. A fresh key is a
 * second command — a second project, a second version, a second run, a second accept in
 * an append-only ledger. When the payload changes the intent is a different one, and a
 * new key is minted; sending a changed payload under the old key is
 * `idempotency_key_reuse`, which is terminal.
 *
 * An intent is identified by an opaque **signature** string. What goes into a signature
 * is the caller's business — the decision entity length-prefixes its parts so a comment
 * containing the separator cannot collide two intents into one — and this module never
 * parses one. It compares.
 */

/** The key currently held for an intent, and the signature of the intent it belongs to. */
export interface IntentRecord {
  readonly signature: string;
  readonly idempotencyKey: string;
}

/**
 * The whole rule, as a pure function: keep the held key while the signature is unchanged,
 * mint a new one when it is not.
 *
 * `mint` is injected so a test can assert *when* a key is minted rather than only what it
 * looks like — which is the difference between a test that can go red on this rule and a
 * test that cannot. Production passes `newIdempotencyKey` from the transport seam.
 */
export function resolveIntentKey(
  previous: IntentRecord | null,
  signature: string,
  mint: () => string,
): IntentRecord {
  if (previous !== null && previous.signature === signature) return previous;
  return { signature, idempotencyKey: mint() };
}
