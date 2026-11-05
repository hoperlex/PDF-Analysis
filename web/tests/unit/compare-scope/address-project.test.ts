/**
 * `R-150c`: the comparison screens follow the header, so the chosen project lives in `?project=`;
 * choosing another drops the parameters that only meant something inside the old one.
 */
import { describe, expect, it } from 'vitest';

import { switchProject } from '@/shared/lib';

describe('the comparison project in the address', () => {
  it('writes the project and drops what belonged to the old one', () => {
    const next = switchProject(new URLSearchParams('project=prj_A&pair=x&set=y&tab=z&foo=bar'), 'prj_B');
    expect(next.get('project')).toBe('prj_B');
    expect(next.get('pair')).toBeNull();
    expect(next.get('set')).toBeNull();
    expect(next.get('tab')).toBeNull();
    expect(next.get('foo')).toBe('bar');
  });

  it('«Все проекты» removes the project', () => {
    expect(switchProject(new URLSearchParams('project=prj_A'), null).get('project')).toBeNull();
  });
});
