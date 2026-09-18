/**
 * What a run spent, and what it observed — as pure functions.
 *
 * Every `it` here names the mutation it exists to redden. The session report records
 * which ones it does redden, measured by applying each mutation to the tree and
 * re-running this file.
 *
 *   M-1  `formatCostMicros` divides by a million and rounds to two places;
 *   M-2  `runCost` reports `0` instead of `absent` when the run made no call;
 *   M-5  `runCost` reports a cost that arrived with no `model_call_count`;
 *   M-8  `diagnosticObservationCount` answers `0` for a count that was not reported;
 *  M-10  a missing `cost_basis` defaults to `measured`.
 */

import { describe, expect, it } from 'vitest';

import {
  costBasisCaption,
  diagnosticObservationCount,
  formatCostMicros,
  runCost,
} from '@/entities/audit-run';

/**
 * M-1. Money is `bigint` millionths and migration `20260910_0002` says floating point
 * money is not stored. The assertion that matters is the sub-cent one: every naive
 * implementation — `/ 1e6` then `toFixed(2)` — prints `0.00` for a real, non-zero cost,
 * which reads as free.
 */
describe('cost_micros is formatted without ever becoming a float (M-1)', () => {
  it('keeps a cost far below a cent instead of rounding it to zero', () => {
    expect(formatCostMicros(1)).toBe('0.000001');
    // The mutation this exists to kill, spelled out: it would print '0.00'.
    expect(formatCostMicros(1)).not.toBe('0.00');
  });

  it('keeps every one of the six fractional digits', () => {
    expect(formatCostMicros(1_234_567)).toBe('1.234567');
    expect(formatCostMicros(999_999)).toBe('0.999999');
  });

  it('renders a whole unit and a zero exactly', () => {
    expect(formatCostMicros(1_000_000)).toBe('1.000000');
    expect(formatCostMicros(0)).toBe('0.000000');
  });

  it('does not lose precision that a float round-trip would lose', () => {
    // A cost with significant digits in both halves. The formatter reproduces the
    // digits of whatever integer it is handed rather than introducing error of its own,
    // which is what a divide-then-round implementation cannot promise.
    const micros = 8_675_309_123_456;
    expect(formatCostMicros(micros)).toBe('8675309.123456');
    expect(formatCostMicros(micros)).toContain(String(micros).slice(-6));
  });

  it('never prints a currency symbol the contract does not name', () => {
    // The contract says "millionths of the provider currency unit" and never names the
    // currency. A `$` here would be an invented fact.
    for (const micros of [0, 1, 1_000_000, 1_234_567]) {
      expect(formatCostMicros(micros)).not.toMatch(/[$£€¥]/);
    }
  });
});

/**
 * M-2. The distinction this programme paid for in `D-3`: "it cost nothing" and "nothing
 * was spent here" are different claims, and the repository keeps them different by
 * returning `None` for a run that never reached the provider.
 */
describe('an absent cost is not a zero cost (M-2)', () => {
  it('reports absent when the run made no provider call', () => {
    expect(runCost({})).toEqual({ kind: 'absent' });
    expect(runCost({ cost_micros: undefined })).toEqual({ kind: 'absent' });
    expect(runCost({ cost_micros: null })).toEqual({ kind: 'absent' });
  });

  it('reports a genuine zero as a reported figure, not as absence', () => {
    const reading = runCost({ cost_micros: 0, cost_basis: 'measured', model_call_count: 2 });
    expect(reading.kind).toBe('reported');
    expect(reading).toMatchObject({ kind: 'reported', micros: 0, callCount: 2 });
  });

  it('gives the two states different kinds, so no caller can merge them by accident', () => {
    const absent = runCost({});
    const free = runCost({ cost_micros: 0, cost_basis: 'measured', model_call_count: 1 });
    expect(absent.kind).not.toBe(free.kind);
  });
});

/**
 * M-5. `D-15` is open: the total sums across retry attempts, so the count is what lets a
 * reader tell a first-try run from a retried one. Printing the sum without it re-creates
 * `D-15` on the screen.
 */
describe('a cost is never reported without the count it sums (M-5)', () => {
  it('refuses a cost that arrived with no model_call_count', () => {
    const reading = runCost({ cost_micros: 4_500, cost_basis: 'estimated' });
    expect(reading.kind).toBe('unreadable');
    // `why` reaches the user -- the screen prints "cannot be read: {why}" -- so the two
    // unreadable causes must not collapse into one sentence. Without this, deleting the
    // missing-count guard is an equivalent mutant: the type guard below catches
    // `undefined` too, and only the reason a reader is given changes.
    expect(reading).toMatchObject({ why: 'it carries a cost with no model call count' });
  });

  it('distinguishes a missing count from a malformed one in what it tells the reader', () => {
    const missing = runCost({ cost_micros: 4_500 });
    const malformed = runCost({ cost_micros: 4_500, model_call_count: 0 });
    expect(missing.kind).toBe('unreadable');
    expect(malformed.kind).toBe('unreadable');
    expect(missing).not.toEqual(malformed);
  });

  it('refuses a cost whose count is zero, which contradicts the cost being present', () => {
    expect(runCost({ cost_micros: 10, model_call_count: 0 }).kind).toBe('unreadable');
  });

  it('refuses a non-integer cost rather than printing a mangled digit string', () => {
    expect(runCost({ cost_micros: 1.5, model_call_count: 1 }).kind).toBe('unreadable');
    expect(runCost({ cost_micros: -1, model_call_count: 1 }).kind).toBe('unreadable');
  });

  it('carries the count through when it is present', () => {
    expect(runCost({ cost_micros: 10, cost_basis: 'estimated', model_call_count: 3 })).toEqual({
      kind: 'reported',
      micros: 10,
      basis: 'estimated',
      callCount: 3,
    });
  });
});

/**
 * M-10. `D-3` was a defaulted provenance field. Defaulting an unstated basis to
 * `measured` would be the same defect, and it would be the flattering direction.
 */
describe('an unstated cost basis is not a measured one (M-10)', () => {
  it('reports a missing basis as null rather than as measured', () => {
    const reading = runCost({ cost_micros: 5, model_call_count: 1 });
    expect(reading).toMatchObject({ kind: 'reported', basis: null });
  });

  it('rejects a basis outside the contract value set', () => {
    const reading = runCost({ cost_micros: 5, model_call_count: 1, cost_basis: 'guessed' });
    expect(reading).toMatchObject({ kind: 'reported', basis: null });
  });

  it('does not phrase estimated as a fault', () => {
    const caption = costBasisCaption('estimated').toLowerCase();
    expect(caption).toContain('not a fault');
    for (const alarm of ['error', 'warning', 'invalid', 'failed', 'unreliable']) {
      expect(caption).not.toContain(alarm);
    }
  });

  it('says what measured actually means', () => {
    expect(costBasisCaption('measured').toLowerCase()).toContain('every call');
  });
});

/** M-8. A count that was not reported is not a count of zero. */
describe('a diagnostic count that was not reported is not zero (M-8)', () => {
  it('answers null when the field is absent', () => {
    expect(diagnosticObservationCount({})).toBeNull();
    expect(diagnosticObservationCount({ diagnostic_observation_count: null })).toBeNull();
  });

  it('answers 0 when the run genuinely observed nothing', () => {
    expect(diagnosticObservationCount({ diagnostic_observation_count: 0 })).toBe(0);
  });

  it('carries a real count through', () => {
    expect(diagnosticObservationCount({ diagnostic_observation_count: 12 })).toBe(12);
  });
});
