/**
 * `screenDecision` — the one answer to "may this session open this screen", which
 * `requireScreen` maps to its redirects and the frame's menu filters by (`W50-SHELL-FRAME`,
 * the integrator's grant of 2026-10-07).
 *
 * `web/tests/guards/screen-guard.guard.test.ts` proves, unedited, that the guard decides as it
 * did before the function moved out of it; this file drives the function directly, including
 * the synthetic role-gated row and the live W51 administrator rows.
 */

import { describe, expect, it } from 'vitest';

import type { ScreenDecision, ScreenEntry } from '@/shared/config';
import { SCREEN_REGISTRY, screenDecision } from '@/shared/config';

import { ADMIN_AND_EXPERT, ADMIN_ONLY, DEFAULT_CREDENTIAL, EXPERT, INCOMPLETE_PROFILE, NO_ROLES, UNKNOWN_ROLE } from './subjects';

const row = (access: ScreenEntry['access'], roles: ScreenEntry['roles'] = 'any'): ScreenEntry => ({
  address: '/fixture',
  label: 'Проба',
  group: 'admin',
  access,
  roles,
  inMenu: true,
});

const PUBLIC = row('public');
const OPEN_TO_DEFAULT = row('open-to-default-credential');
const ANY_SESSION = row('session');
const ADMIN_ROW = row('session', ['admin']);

describe('the four decisions, in order', () => {
  it('1. a guest opens public screens and is sent to sign in from every other', () => {
    expect(screenDecision(PUBLIC, null)).toBe('open');
    expect(screenDecision(OPEN_TO_DEFAULT, null)).toBe('sign-in');
    expect(screenDecision(ANY_SESSION, null)).toBe('sign-in');
    expect(screenDecision(ADMIN_ROW, null)).toBe('sign-in');
  });

  it('2. a default credential opens no session screen, before anything else is asked', () => {
    // Also an incomplete profile and an admin-only row: the password comes first.
    expect(DEFAULT_CREDENTIAL.profileComplete).toBe(false);
    expect(screenDecision(ANY_SESSION, DEFAULT_CREDENTIAL)).toBe('change-password');
    expect(screenDecision(ADMIN_ROW, { ...DEFAULT_CREDENTIAL, roles: ['expert'] })).toBe('change-password');
    expect(screenDecision(OPEN_TO_DEFAULT, DEFAULT_CREDENTIAL)).toBe('open');
    expect(screenDecision(PUBLIC, DEFAULT_CREDENTIAL)).toBe('open');
  });

  it('3. an incomplete profile opens no session screen, and is asked before the roles', () => {
    expect(screenDecision(ANY_SESSION, INCOMPLETE_PROFILE)).toBe('complete-profile');
    expect(screenDecision(ADMIN_ROW, { ...INCOMPLETE_PROFILE, roles: ['expert'] })).toBe('complete-profile');
    expect(screenDecision(OPEN_TO_DEFAULT, INCOMPLETE_PROFILE)).toBe('open');
  });

  it('4. a role-gated screen needs any one of its roles', () => {
    expect(screenDecision(ADMIN_ROW, ADMIN_ONLY)).toBe('open');
    expect(screenDecision(ADMIN_ROW, ADMIN_AND_EXPERT)).toBe('open');
    expect(screenDecision(ADMIN_ROW, EXPERT)).toBe('forbidden');
    expect(screenDecision(ADMIN_ROW, NO_ROLES)).toBe('forbidden');
    expect(screenDecision(row('session', ['expert', 'admin']), ADMIN_ONLY)).toBe('open');
    expect(screenDecision(ANY_SESSION, NO_ROLES)).toBe('open');
  });

  it('an unknown role value matches no row and is never read as any', () => {
    const unknownOnly = { ...UNKNOWN_ROLE, roles: ['auditor'] };
    expect(screenDecision(ADMIN_ROW, unknownOnly)).toBe('forbidden');
    expect(screenDecision(ANY_SESSION, unknownOnly)).toBe('open');
    expect(screenDecision(row('session', ['expert']), UNKNOWN_ROLE)).toBe('open');
  });

  it('answers only the five values the guard maps', () => {
    const seen = new Set<ScreenDecision>();
    for (const screen of [PUBLIC, OPEN_TO_DEFAULT, ANY_SESSION, ADMIN_ROW]) {
      for (const who of [null, EXPERT, NO_ROLES, DEFAULT_CREDENTIAL, INCOMPLETE_PROFILE]) {
        seen.add(screenDecision(screen, who));
      }
    }
    expect([...seen].sort()).toEqual(['change-password', 'complete-profile', 'forbidden', 'open', 'sign-in']);
  });
});

describe('the live registry', () => {
  it('has exactly three administrator-only rows', () => {
    expect(SCREEN_REGISTRY.filter((screen) => screen.roles !== 'any').map((screen) => screen.address)).toEqual([
      '/admin/users', '/admin/users/[user_uid]', '/admin/registrations',
    ]);
  });

  it('admits admins to every menu row, and an expert only to non-admin rows', () => {
    const menu = SCREEN_REGISTRY.filter((screen) => screen.inMenu);
    expect(menu.length).toBeGreaterThan(0);
    for (const screen of menu) {
      expect(screenDecision(screen, ADMIN_ONLY), screen.address).toBe('open');
      expect(screenDecision(screen, EXPERT), screen.address).toBe(screen.group === 'admin' ? 'forbidden' : 'open');
      expect(screenDecision(screen, NO_ROLES), screen.address).toBe(screen.group === 'admin' ? 'forbidden' : 'open');
      expect(screenDecision(screen, null), screen.address).toBe('sign-in');
      expect(screenDecision(screen, DEFAULT_CREDENTIAL), screen.address).toBe('change-password');
    }
  });
});
