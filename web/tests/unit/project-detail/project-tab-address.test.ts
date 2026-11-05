/**
 * `UI-A-22`: the project page's tab lives in the address (`?tab=`): a link, a reload and «Назад» return to
 * it. An absent or unknown value is the first tab.
 */
import { describe, expect, it } from 'vitest';

import { tabOf } from '@/_pages/project-detail/ui/project-detail-page';

describe('the project tab in the address', () => {
  it('reads a known tab', () => {
    expect(tabOf('documents')).toBe('documents');
    expect(tabOf('optimisation')).toBe('optimisation');
  });

  it('falls to the first tab when the value is absent or unknown', () => {
    expect(tabOf(null)).toBe('documents');
    expect(tabOf('')).toBe('documents');
    expect(tabOf('settings')).toBe('documents');
  });
});
