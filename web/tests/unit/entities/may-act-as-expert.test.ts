/**
 * `R-150e`: the screens stop offering an expert's action to an account known to hold no `expert`
 * («Наблюдатель», or an administrator alone). The server refuses it in any case; while the account is
 * not known yet, the control stays drawn and the operation answers for itself.
 */
import { describe, expect, it } from 'vitest';

import { mayActAsExpert } from '@/entities/account';

describe('mayActAsExpert', () => {
  it('offers the action while the account is not known yet', () => {
    expect(mayActAsExpert(undefined)).toBe(true);
  });

  it('offers it to an expert, alone or beside admin', () => {
    expect(mayActAsExpert(['expert'])).toBe(true);
    expect(mayActAsExpert(['admin', 'expert'])).toBe(true);
  });

  it('withholds it from the viewer and from an administrator alone', () => {
    expect(mayActAsExpert(['viewer'])).toBe(false);
    expect(mayActAsExpert(['admin'])).toBe(false);
    expect(mayActAsExpert([])).toBe(false);
  });
});
