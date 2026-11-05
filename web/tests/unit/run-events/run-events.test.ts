/**
 * `UI-B-39`: the run page's «События прогона» is the journal filtered to the run; an operator's read
 * (`R-150w`), not offered to a viewer.
 */
import { describe, expect, it } from 'vitest';

import { mayReadJournal } from '@/_pages/run/ui/run-events';

describe('who sees the run events', () => {
  it('an expert or an administrator, and an account not known yet', () => {
    expect(mayReadJournal(['expert'])).toBe(true);
    expect(mayReadJournal(['admin'])).toBe(true);
    expect(mayReadJournal(undefined)).toBe(true);
  });

  it('never a viewer, nor an account with no role', () => {
    expect(mayReadJournal(['viewer'])).toBe(false);
    expect(mayReadJournal([])).toBe(false);
  });
});
