import { afterEach, describe, expect, it } from 'vitest';

import { VersionCheckError, checkWebVersion, shouldShowUpdate } from '@/shared/api';

const prior = process.env.NEXT_PUBLIC_WEB_BUILD_ID;
afterEach(() => {
  if (prior === undefined) delete process.env.NEXT_PUBLIC_WEB_BUILD_ID;
  else process.env.NEXT_PUBLIC_WEB_BUILD_ID = prior;
});

describe('web build check', () => {
  it('compares the served build with the bundle and never treats an equal build as an update', async () => {
    process.env.NEXT_PUBLIC_WEB_BUILD_ID = 'w-old';
    const equal = await checkWebVersion(async () => Response.json({ web_build_id: 'w-old' }));
    const changed = await checkWebVersion(async () => Response.json({ web_build_id: 'w-new' }));
    expect(equal.changed).toBe(false);
    expect(changed).toEqual({ current: 'w-old', available: 'w-new', changed: true });
  });

  it('hides only the build postponed with Later', () => {
    expect(shouldShowUpdate('w-old', 'w-new', null)).toBe(true);
    expect(shouldShowUpdate('w-old', 'w-new', 'w-new')).toBe(false);
    expect(shouldShowUpdate('w-old', 'w-next', 'w-new')).toBe(true);
    expect(shouldShowUpdate('w-old', 'w-old', null)).toBe(false);
  });

  it('refuses malformed and failed readings instead of inventing an ID', async () => {
    process.env.NEXT_PUBLIC_WEB_BUILD_ID = 'w-old';
    await expect(checkWebVersion(async () => Response.json({ wrong: 'w-new' }))).rejects.toBeInstanceOf(VersionCheckError);
    await expect(checkWebVersion(async () => new Response(null, { status: 401 }))).rejects.toMatchObject({ status: 401 });
    await expect(checkWebVersion(async () => { throw new Error('offline'); })).rejects.toMatchObject({ status: null });
  });
});
