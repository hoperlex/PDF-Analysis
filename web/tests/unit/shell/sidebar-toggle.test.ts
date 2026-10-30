import { describe, expect, it } from 'vitest';

import { readSidebarMode, SIDEBAR_STORAGE_KEY, writeSidebarMode } from '@/_app/sidebar-toggle';

describe('desktop sidebar preference', () => {
  it('defaults to full and accepts only the compact stored value', () => {
    expect(readSidebarMode(null)).toBe('full');
    expect(readSidebarMode({ getItem: () => 'compact', setItem: () => undefined })).toBe('compact');
    expect(readSidebarMode({ getItem: () => 'invalid', setItem: () => undefined })).toBe('full');
    expect(readSidebarMode({ getItem: () => { throw new Error('blocked'); }, setItem: () => undefined })).toBe('full');
  });

  it('persists the requested state when storage is available', () => {
    const written: [string, string][] = [];
    writeSidebarMode({ getItem: () => null, setItem: (key, value) => { written.push([key, value]); } }, 'compact');
    expect(written).toEqual([[SIDEBAR_STORAGE_KEY, 'compact']]);
    expect(() => writeSidebarMode({ getItem: () => null, setItem: () => { throw new Error('blocked'); } }, 'full')).not.toThrow();
  });
});
