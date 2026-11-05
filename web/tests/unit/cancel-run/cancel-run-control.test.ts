/**
 * `UI-A-62`: «Отменить прогон» is offered for a run that has not ended, to an expert or an administrator.
 */
import { describe, expect, it } from 'vitest';

import { cancellable, mayCancel } from '@/features/cancel-run';

describe('the run page offers a cancel', () => {
  it('for a run that has not ended', () => {
    for (const state of ['created', 'queued', 'running', 'validating'] as const) expect(cancellable(state)).toBe(true);
    for (const state of ['published', 'partial', 'failed', 'cancelled'] as const) expect(cancellable(state)).toBe(false);
    expect(cancellable(undefined)).toBe(false);
  });

  it('to an expert or an administrator, never to a viewer', () => {
    expect(mayCancel(['expert'])).toBe(true);
    expect(mayCancel(['admin'])).toBe(true);
    expect(mayCancel(['viewer'])).toBe(false);
    expect(mayCancel([])).toBe(false);
    expect(mayCancel(undefined)).toBe(true);
  });
});
