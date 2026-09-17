/**
 * Two different decision intents never produce one signature.
 *
 * `intentSignature` length-prefixes its parts rather than joining them with a separator,
 * because a signature collision has a specific and unrecoverable consequence: the second
 * command is suppressed as a retry of the first, and the ledger is append-only, so there
 * is nothing to undo afterwards.
 *
 * The existing collision test uses `a|comment` against an observation id ending in
 * `|comment`, and those two stay distinct under a naive `join('|')` as well — so it did
 * not distinguish the length-prefixed form from the naive one. The pair below does: under
 * `[event_type, finding_observation_id, comment].join('|')` both sides are the same
 * string, `comment|fobs_...|a|b`.
 */

import { describe, expect, it } from 'vitest';

import { intentSignature } from '@/entities/expert-decision';

const OBSERVATION_ID = 'fobs_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';

/** Separators a join might plausibly use. The rule must hold for all of them. */
const SEPARATORS = ['|', ':', '/', '#', '-'] as const;

describe('a separator inside a part cannot be mistaken for the separator between parts', () => {
  it('keeps a comment containing the separator apart from an id containing it', () => {
    const shifted = intentSignature({
      event_type: 'comment',
      finding_observation_id: OBSERVATION_ID,
      comment: 'a|b',
    });
    const unshifted = intentSignature({
      event_type: 'comment',
      finding_observation_id: `${OBSERVATION_ID}|a`,
      comment: 'b',
    });

    // Under a naive join both of these are `comment|fobs_...|a|b`.
    expect(shifted).not.toBe(unshifted);
  });

  it('keeps the same pair apart for every other separator a join might use', () => {
    for (const separator of SEPARATORS) {
      const left = intentSignature({
        event_type: 'comment',
        finding_observation_id: OBSERVATION_ID,
        comment: `a${separator}b`,
      });
      const right = intentSignature({
        event_type: 'comment',
        finding_observation_id: `${OBSERVATION_ID}${separator}a`,
        comment: 'b',
      });
      expect(left, `separator ${JSON.stringify(separator)} collided`).not.toBe(right);
    }
  });

  it('still gives one intent one signature', () => {
    // The other half: the property is injectivity, not merely producing different strings.
    const once = intentSignature({
      event_type: 'accept',
      finding_observation_id: OBSERVATION_ID,
      comment: 'a|b',
    });
    const twice = intentSignature({
      event_type: 'accept',
      finding_observation_id: OBSERVATION_ID,
      comment: 'a|b',
    });
    expect(once).toBe(twice);
  });
});
