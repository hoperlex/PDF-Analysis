/**
 * `C-29` (W53 close): release notices read once per trigger, survive a build without its
 * identifier and keep one tab-return listener.
 *
 * The render harness runs no effect, so the triggers are tested through the two functions
 * `ReleaseNotices` wires them with, and the wiring itself through the module's source.
 */

import { readFileSync } from 'node:fs';
import { createElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';

import {
  ReleaseNotices, bundleBuildId, listenForTabReturn, readOnRoute,
} from '@/_app/release-notices';
import type { NoticeReads, TabDocument } from '@/_app/release-notices';

import { newClient, renderScreen } from '../screens/harness';

const BUILD_VARIABLE = 'NEXT_PUBLIC_WEB_BUILD_ID';
const prior = process.env[BUILD_VARIABLE];

afterEach(() => {
  if (prior === undefined) delete process.env[BUILD_VARIABLE];
  else process.env[BUILD_VARIABLE] = prior;
});

function counted(): NoticeReads & { readonly calls: string[] } {
  const calls: string[] = [];
  return { calls, version: () => calls.push('version'), releases: () => calls.push('releases') };
}

function fakeDocument(): TabDocument & {
  visibilityState: DocumentVisibilityState;
  readonly listeners: Map<string, Set<() => void>>;
  fire(type: string): void;
} {
  const listeners = new Map<string, Set<() => void>>();
  return {
    visibilityState: 'visible',
    listeners,
    addEventListener(type, listener) {
      if (!listeners.has(type)) listeners.set(type, new Set());
      listeners.get(type)!.add(listener);
    },
    removeEventListener(type, listener) { listeners.get(type)?.delete(listener); },
    fire(type) { for (const listener of listeners.get(type) ?? []) listener(); },
  };
}

describe('a missing web build id', () => {
  it('disables the banner instead of throwing during render', () => {
    delete process.env[BUILD_VARIABLE];
    expect(bundleBuildId()).toBeNull();
    expect(() => renderScreen(newClient(), createElement(ReleaseNotices))).not.toThrow();
    expect(renderScreen(newClient(), createElement(ReleaseNotices))).not.toContain('data-update-banner');
  });

  it('is still read when the build carries one', () => {
    process.env[BUILD_VARIABLE] = 'w-current';
    expect(bundleBuildId()).toBe('w-current');
  });
});

describe('notice triggers', () => {
  it('reads only the version on mount: the list is already being fetched by its query', () => {
    const reads = counted();
    readOnRoute('/projects', '/projects', reads);
    expect(reads.calls).toEqual(['version']);
  });

  it('re-reads both on a route change', () => {
    const reads = counted();
    readOnRoute('/projects', '/queue', reads);
    expect(reads.calls).toEqual(['version', 'releases']);
  });

  it('listens to visibilitychange only, reads each once per return, and detaches', () => {
    const reads = counted();
    const target = fakeDocument();
    const detach = listenForTabReturn(target, reads);
    expect([...target.listeners.keys()]).toEqual(['visibilitychange']);
    target.visibilityState = 'hidden';
    target.fire('visibilitychange');
    expect(reads.calls).toEqual([]);
    target.visibilityState = 'visible';
    target.fire('visibilitychange');
    expect(reads.calls).toEqual(['version', 'releases']);
    detach();
    target.fire('visibilitychange');
    expect(reads.calls).toEqual(['version', 'releases']);
  });

  it('is wired with no focus listener and no direct refetch on mount', () => {
    const source = readFileSync(new URL('../../../src/_app/release-notices.tsx', import.meta.url), 'utf8');
    expect(source).not.toMatch(/addEventListener\(\s*['"]focus['"]/);
    expect(source).toMatch(/listenForTabReturn\(document, reads\)/);
    expect(source).toMatch(/readOnRoute\(previous, pathname, reads\)/);
    expect(source.match(/void refetch\(\)/g) ?? []).toHaveLength(1);
    expect(source).not.toMatch(/=\s*getWebBuildId\(\)/);
  });
});
