/**
 * «N записей»: the journal's `total` with its noun in agreement (`UI-PARITY-P0A`).
 *
 * A bare «N записей» for every N reads wrongly for one in three of them. The rule is the Russian
 * one: 1 and 21 take «запись», 2–4 and 22–24 «записи», everything else «записей», and the teens
 * 11–14 are «записей» whatever their last digit.
 */

import { describe, expect, it } from 'vitest';

import { recordCountLabel } from '@/entities/expert-decision';

describe('recordCountLabel declines the noun with the number', () => {
  const cases: readonly (readonly [number, string])[] = [
    [0, '0 записей'],
    [1, '1 запись'],
    [2, '2 записи'],
    [4, '4 записи'],
    [5, '5 записей'],
    [10, '10 записей'],
    [11, '11 записей'],
    [12, '12 записей'],
    [14, '14 записей'],
    [21, '21 запись'],
    [22, '22 записи'],
    [25, '25 записей'],
    [100, '100 записей'],
    [101, '101 запись'],
    [111, '111 записей'],
    [112, '112 записей'],
    [120, '120 записей'],
  ];

  for (const [total, label] of cases) {
    it(`${total} -> ${label}`, () => {
      expect(recordCountLabel(total)).toBe(label);
    });
  }

  it('can fail: the label for 2 is not the label for 5', () => {
    expect(recordCountLabel(2)).not.toBe(recordCountLabel(5));
  });
});
