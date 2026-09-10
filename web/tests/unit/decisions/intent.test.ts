/**
 * One idempotency key per intent, reused on every retry.
 *
 * Seam §4.3. The consequence of getting this wrong is not a failed request, it is a second
 * event in an append-only ledger — the reviewer pressed Accept once, it failed, they pressed
 * it again, and the finding now carries two accepts and there is nothing to delete.
 *
 * The rule is a pure function over the previously recorded intent, so it can be tested
 * exactly, with a counting mint, instead of by rendering a component and hoping.
 */

import { describe, expect, it } from 'vitest';

import { intentSignature, resolveIntentKey } from '@/entities/expert-decision';
import { checkComment } from '@/features/append-comment';
import type { AppendDecisionRequest } from '@/shared/api';

import { OBSERVATION_ID } from '../review/fixtures';

function counter() {
  let n = 0;
  return {
    mint: () => `idem-${(n += 1)}`,
    get count() {
      return n;
    },
  };
}

const ACCEPT: AppendDecisionRequest = {
  event_type: 'accept',
  finding_observation_id: OBSERVATION_ID,
};

describe('resolveIntentKey', () => {
  it('mints a key the first time an intent is expressed', () => {
    const mint = counter();
    const record = resolveIntentKey(null, ACCEPT, mint.mint);
    expect(record.idempotencyKey).toBe('idem-1');
    expect(mint.count).toBe(1);
  });

  it('reuses the key when the same intent is retried', () => {
    const mint = counter();
    const first = resolveIntentKey(null, ACCEPT, mint.mint);
    const retry = resolveIntentKey(first, ACCEPT, mint.mint);
    const retryAgain = resolveIntentKey(retry, ACCEPT, mint.mint);

    expect(retry.idempotencyKey).toBe(first.idempotencyKey);
    expect(retryAgain.idempotencyKey).toBe(first.idempotencyKey);
    // Minted once, across three attempts. A fresh key would be a second command.
    expect(mint.count).toBe(1);
  });

  it('mints a new key when the user presses a different button', () => {
    const mint = counter();
    const accept = resolveIntentKey(null, ACCEPT, mint.mint);
    const reject = resolveIntentKey(accept, { ...ACCEPT, event_type: 'reject' }, mint.mint);

    expect(reject.idempotencyKey).not.toBe(accept.idempotencyKey);
    expect(mint.count).toBe(2);
  });

  it('mints a new key when the observation being judged changes', () => {
    // A verdict is recorded against the evidence in front of the reviewer, not against
    // whatever the newest run later produced, so a different observation is a different
    // command even for the same finding.
    const mint = counter();
    const first = resolveIntentKey(null, ACCEPT, mint.mint);
    const other = resolveIntentKey(
      first,
      { ...ACCEPT, finding_observation_id: 'fobs_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z' },
      mint.mint,
    );
    expect(other.idempotencyKey).not.toBe(first.idempotencyKey);
  });

  it('treats an edited comment as a different intent', () => {
    const mint = counter();
    const draft: AppendDecisionRequest = {
      event_type: 'comment',
      finding_observation_id: OBSERVATION_ID,
      comment: 'first wording',
    };
    const first = resolveIntentKey(null, draft, mint.mint);
    const retrySame = resolveIntentKey(first, draft, mint.mint);
    const edited = resolveIntentKey(retrySame, { ...draft, comment: 'second wording' }, mint.mint);

    expect(retrySame.idempotencyKey).toBe(first.idempotencyKey);
    expect(edited.idempotencyKey).not.toBe(first.idempotencyKey);
    expect(mint.count).toBe(2);
  });
});

describe('intentSignature', () => {
  it('does not collide when a comment contains the separator characters', () => {
    // A naive `join('|')` would let a crafted comment forge another intent's signature,
    // and the consequence of that collision is a suppressed second command.
    const a = intentSignature({
      event_type: 'comment',
      finding_observation_id: OBSERVATION_ID,
      comment: 'a|comment',
    });
    const b = intentSignature({
      event_type: 'comment',
      finding_observation_id: OBSERVATION_ID,
      comment: 'a',
    });
    const c = intentSignature({
      event_type: 'comment',
      finding_observation_id: `${OBSERVATION_ID}|comment`,
      comment: 'a',
    });

    expect(new Set([a, b, c]).size).toBe(3);
  });

  it('treats an absent comment and an empty comment as the same intent', () => {
    expect(
      intentSignature({ event_type: 'accept', finding_observation_id: OBSERVATION_ID }),
    ).toBe(
      intentSignature({
        event_type: 'accept',
        finding_observation_id: OBSERVATION_ID,
        comment: '',
      }),
    );
  });
});

describe('the comment check', () => {
  it('refuses an empty comment before it becomes a ledger row', () => {
    // Not a second validation of the contract — the server stays the authority. It is
    // refusing to append an event to a ledger that cannot delete one.
    expect(checkComment('')).toEqual({ kind: 'refused', refusal: 'empty' });
    expect(checkComment('   \n\t ')).toEqual({ kind: 'refused', refusal: 'empty' });
  });

  it('trims the whitespace a textarea collects and changes nothing else', () => {
    expect(checkComment('  the 45-day term is operative  ')).toEqual({
      kind: 'ok',
      comment: 'the 45-day term is operative',
    });
    // Interior whitespace, punctuation and Cyrillic are the reviewer's words, untouched.
    expect(checkComment('см.  §4 — «Исполнитель»')).toEqual({
      kind: 'ok',
      comment: 'см.  §4 — «Исполнитель»',
    });
  });
});
