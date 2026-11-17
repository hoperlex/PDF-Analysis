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
  ReleaseNotices, bundleBuildId, listenForTabReturn, noticesOn, readOnRoute, signInAfterRefusal,
} from '@/_app/release-notices';
import type { NoticeReads, NoticeWants, TabDocument } from '@/_app/release-notices';

import {
  HOME_SCREEN, NEXT_PARAM, RETURN_PATH_MAX_LENGTH, SCREEN_REGISTRY, SIGN_IN_SCREEN, safeReturnPath,
} from '@/shared/config';
import { SESSION_END_REASONS, SESSION_END_REASON_PARAM, isSessionEndReason, sessionEndReasonOf } from '@/shared/lib';

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

describe('«Что нового» stands on the home screen only (UIP-G-16, Г12-B)', () => {
  const everything: NoticeWants = { banner: true, whatsNew: true, markFault: true };

  it('shows the strip, and the failed mark that follows its «Закрыть», on «Главная»', () => {
    expect(HOME_SCREEN).toBe('/');
    expect(noticesOn(HOME_SCREEN, everything)).toEqual(everything);
  });

  it('shows neither on any other registered screen, and on an unknown or unread address', () => {
    const others = SCREEN_REGISTRY.map((row) => row.address as string).filter((address) => address !== HOME_SCREEN);
    expect(others.length).toBeGreaterThan(10);
    for (const address of [...others, '/nowhere-registered', null]) {
      expect(noticesOn(address, everything), String(address)).toEqual({ banner: true, whatsNew: false, markFault: false });
    }
  });

  it('keeps «Доступна новая версия» on every screen: it is not «Что нового»', () => {
    for (const address of [HOME_SCREEN, '/projects', '/queue', '/account', null]) {
      expect(noticesOn(address, { banner: true, whatsNew: false, markFault: false }).banner, String(address)).toBe(true);
      expect(noticesOn(address, { banner: false, whatsNew: true, markFault: true }).banner, String(address)).toBe(false);
    }
  });

  it('asks for nothing that was not asked: no strip appears from a false want, on the home screen too', () => {
    expect(noticesOn(HOME_SCREEN, { banner: false, whatsNew: false, markFault: false }))
      .toEqual({ banner: false, whatsNew: false, markFault: false });
  });

  it('is what the component renders by: every strip is read from the filtered result', () => {
    const source = readFileSync(new URL('../../../src/_app/release-notices.tsx', import.meta.url), 'utf8');
    expect(source).toMatch(/noticesOn\(pathname, \{/);
    expect(source).toMatch(/shown\.banner/);
    expect(source).toMatch(/shown\.whatsNew/);
    expect(source).toMatch(/shown\.markFault/);
    // no strip is rendered from its own flag any more
    expect(source).not.toMatch(/\{markFault \?/);
    expect(source).not.toMatch(/\{whatsNewShown/);
  });
});

describe('a 401 sends the browser to sign-in with the reason it knows', () => {
  const parsed = (address: string) => new URL(address, 'https://x.invalid');

  it('carries `ended` and the page it was on: /login?next=…&reason=ended', () => {
    const address = signInAfterRefusal({ pathname: '/projects', search: '?tab=archived' });
    expect(address).toBe('/login?next=%2Fprojects%3Ftab%3Darchived&reason=ended');
    expect(parsed(address).pathname).toBe(SIGN_IN_SCREEN);
    // The same two parameters in the same order as the server guard's `/login?next=…&reason=…`.
    expect([...parsed(address).searchParams.keys()]).toEqual([NEXT_PARAM, SESSION_END_REASON_PARAM]);
    // What the sign-in screen reads back is the validator's own answer for the same value.
    expect(safeReturnPath(parsed(address).searchParams.get(NEXT_PARAM))).toBe('/projects?tab=archived');
  });

  it('says a word of the closed list, and reads back through the closed list\'s own reader', () => {
    const reason = parsed(signInAfterRefusal({ pathname: '/projects', search: '' })).searchParams.get(SESSION_END_REASON_PARAM);
    expect(isSessionEndReason(reason)).toBe(true);
    expect(SESSION_END_REASONS).toContain(reason);
    expect(sessionEndReasonOf(reason)).toBe('ended');
  });

  it('keeps the reason when there is no `next` to carry', () => {
    const bare = '/login?reason=ended';
    expect(signInAfterRefusal({ pathname: '/projects', search: '' })).toBe('/login?next=%2Fprojects&reason=ended');
    // an address the registry does not know, a query it refuses, and one over the length limit
    expect(signInAfterRefusal({ pathname: '/nowhere-registered', search: '' })).toBe(bare);
    expect(signInAfterRefusal({ pathname: '/projects', search: '?q=<x>' })).toBe(bare);
    expect(signInAfterRefusal({ pathname: '/projects', search: `?q=${'a'.repeat(RETURN_PATH_MAX_LENGTH)}` })).toBe(bare);
    // the sign-in screen is never its own `next`
    expect(signInAfterRefusal({ pathname: SIGN_IN_SCREEN, search: '?reason=expired' })).toBe(bare);
  });

  it('is what both 401 sites call: no bare sign-in redirect is left in the module', () => {
    const source = readFileSync(new URL('../../../src/_app/release-notices.tsx', import.meta.url), 'utf8');
    expect(source.match(/window\.location\.assign\(signInAfterRefusal\(window\.location\)\)/g) ?? []).toHaveLength(2);
    expect(source.match(/location\.assign\(/g) ?? []).toHaveLength(2);
    expect(source).not.toMatch(/assign\(\s*SIGN_IN_SCREEN\s*\)/);
    // the word is typed against the list, never a free string in a call
    expect(source).toMatch(/REFUSED_BY_API: SessionEndReason = 'ended'/);
  });

  it('can fail: the bare redirect it replaces carries no reason and no `next`', () => {
    const address = SIGN_IN_SCREEN;
    expect(sessionEndReasonOf(parsed(address).searchParams.get(SESSION_END_REASON_PARAM))).toBeNull();
    expect(parsed(address).searchParams.get(NEXT_PARAM)).toBeNull();
    expect(parsed(signInAfterRefusal({ pathname: '/projects', search: '' })).searchParams.get(NEXT_PARAM)).not.toBeNull();
  });
});
