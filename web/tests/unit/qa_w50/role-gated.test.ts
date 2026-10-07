/**
 * `W50-QA-01`, items 6 and 8 — `admin` screens are absent from the menu for an expert, and the
 * `/403` screen for every role-gated row names the role the registry requires.
 *
 * W50 registers **no** role-gated row (`R-60`: reading needs no role, and the `admin` rows are
 * W51's). So each item is two tests, and they must not be read as one:
 *
 *   1. a **fixture registry** — the live rows plus role-gated ones of every shape (an `admin`
 *      group with a static and a dynamic row, an `expert`-only row, an any-of row) — through the
 *      same functions the frame and the guard use (`buildNavigation`, `enforceScreen`,
 *      `requiredRolesFor`, `ForbiddenPage`): this is what proves the mechanism;
 *   2. the **live registry's** role-gated set, asserted to be exactly what W50 ships — empty —
 *      so that the fixture case is never mistaken for coverage of a live row. When W51 adds a
 *      row, the second test reddens and points here.
 *
 * Written by QA from the plan, without the lane reports.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { newClient, renderScreen } from '../screens/harness';

import { buildNavigation } from '@/_app/navigation';
import { FrameNavigationView } from '@/_app/frame-navigation';
import { ForbiddenPage } from '@/_pages/forbidden';
import type { SessionAccount } from '@/app/bff/session/store';
import { forgetEverySession, openSession } from '@/app/bff/session/store';
import { ROLE_LABELS } from '@/entities/account';
import type { Role } from '@/shared/api';
import type { ScreenDecisionSubject, ScreenEntry } from '@/shared/config';
import { SCREEN_REGISTRY, requiredRolesFor } from '@/shared/config';

const jar = vi.hoisted(() => ({ value: null as string | null }));

vi.mock('next/headers', () => ({
  cookies: async () => ({
    get: (name: string) => (jar.value === null ? undefined : { name, value: jar.value }),
  }),
}));

const { enforceScreen } = await import('@/app/bff/session/screen-lock');
const { default: ForbiddenRoute } = await import('@/app/403/page');

// ---------------------------------------------------------------------------- the fixture

const USER = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';

/** Role-gated rows of every shape W51 might add. None is in the live registry. */
const GATED: readonly ScreenEntry[] = [
  { address: '/admin/users', label: 'Учётные записи', group: 'admin', access: 'session', roles: ['admin'], inMenu: true },
  { address: '/admin/registrations', label: 'Заявки', group: 'admin', access: 'session', roles: ['admin'], inMenu: true },
  {
    address: '/admin/users/[user_uid]',
    label: 'Учётная запись',
    group: 'admin',
    access: 'session',
    roles: ['admin'],
    inMenu: false,
  },
  { address: '/expert-desk', label: 'Стол эксперта', group: 'work', access: 'session', roles: ['expert'], inMenu: true },
  {
    address: '/review-board',
    label: 'Совет',
    group: 'system',
    access: 'session',
    roles: ['expert', 'admin'],
    inMenu: true,
  },
];

const FIXTURE: readonly ScreenEntry[] = [...SCREEN_REGISTRY, ...GATED];

const COMPLETE: SessionAccount = {
  login: 'qa-reviewer@qa.invalid',
  displayLabel: 'Проверка К. А.',
  initials: 'ПК',
  roles: ['expert'],
  isDefaultCredential: false,
  profileComplete: true,
};

function subject(roles: readonly string[]): ScreenDecisionSubject {
  return { roles, isDefaultCredential: false, profileComplete: true };
}

const EXPERT = subject(['expert']);
const ADMIN = subject(['admin']);
const BOTH = subject(['expert', 'admin']);
const NONE = subject([]);

function addressesIn(navigation: ReturnType<typeof buildNavigation>): string[] {
  return [
    ...(navigation.home === null ? [] : [navigation.home.address]),
    ...navigation.groups.flatMap((group) => group.items.map((item) => item.address)),
  ];
}

// ------------------------------------------------------------------- 6. absent from the menu

describe('6 (fixture): admin screens are absent from the menu for an expert', () => {
  it('an expert gets no Администрирование group and no /admin address', () => {
    const navigation = buildNavigation(EXPERT, FIXTURE);
    expect(navigation.groups.map((group) => group.group)).not.toContain('admin');
    expect(addressesIn(navigation).filter((address) => address.startsWith('/admin'))).toEqual([]);
    // The expert-gated row IS offered to the expert: the filter is by role, not by group.
    expect(addressesIn(navigation)).toContain('/expert-desk');
  });

  it('an empty role set gets none of the role-gated rows, the any-of row included', () => {
    const navigation = buildNavigation(NONE, FIXTURE);
    expect(navigation.groups.map((group) => group.group)).not.toContain('admin');
    const offered = addressesIn(navigation);
    expect(offered.filter((address) => GATED.some((row) => row.address === address))).toEqual([]);
  });

  it('an administrator gets the group, named, with its menu rows in registry order', () => {
    const navigation = buildNavigation(ADMIN, FIXTURE);
    const admin = navigation.groups.find((group) => group.group === 'admin');
    expect(admin?.label).toBe('Администрирование');
    expect(admin?.items.map((item) => item.address)).toEqual(['/admin/users', '/admin/registrations']);
    // The dynamic row is never a menu link.
    expect(addressesIn(navigation)).not.toContain('/admin/users/[user_uid]');
    expect(addressesIn(navigation)).not.toContain('/expert-desk');
    expect(addressesIn(navigation)).toContain('/review-board');
  });

  it('the rendered navigation for an expert names no administration group and links no /admin address', () => {
    const forExpert = renderToStaticMarkup(
      createElement(FrameNavigationView, { navigation: buildNavigation(EXPERT, FIXTURE), pathname: '/' }),
    );
    expect(forExpert).not.toContain('Администрирование');
    expect(forExpert).not.toMatch(/href="\/admin/);
    // And the same render for an administrator does — so the absence above is a filter, not a renderer that drops the group.
    const forAdmin = renderToStaticMarkup(
      createElement(FrameNavigationView, { navigation: buildNavigation(BOTH, FIXTURE), pathname: '/' }),
    );
    expect(forAdmin).toContain('Администрирование');
    expect(forAdmin).toMatch(/href="\/admin\/users"/);
  });

  it('a default credential and an incomplete profile get no group at all, admin roles or not', () => {
    for (const changes of [{ isDefaultCredential: true }, { profileComplete: false }]) {
      const navigation = buildNavigation({ ...BOTH, ...changes }, FIXTURE);
      expect(navigation.groups, JSON.stringify(changes)).toEqual([]);
      expect(navigation.home, JSON.stringify(changes)).toBeNull();
    }
  });
});

describe('6 (live): W50 registers no role-gated row, so the fixture above is the only coverage', () => {
  it('the live role-gated set is empty (R-60), and no live row is in the admin group', () => {
    const rows: readonly ScreenEntry[] = SCREEN_REGISTRY;
    expect(rows.filter((row) => row.roles !== 'any').map((row) => row.address)).toEqual([]);
    expect(rows.filter((row) => row.group === 'admin').map((row) => row.address)).toEqual([]);
  });

  it('so no session sees an administration group in the live menu, an administrator included', () => {
    for (const who of [EXPERT, ADMIN, BOTH, NONE]) {
      expect(buildNavigation(who).groups.map((group) => group.group)).not.toContain('admin');
    }
  });
});

// ------------------------------------------------------------- 8. /403 names the role

const PROPS_QUERY = { tab: 'all' } as const;

function concrete(row: ScreenEntry): { readonly path: string; readonly params: Record<string, string> } {
  const params: Record<string, string> = {};
  const path = row.address.replace(/\[([^\]]+)\]/g, (_, name: string) => {
    params[name] = USER;
    return USER;
  });
  return { path, params };
}

async function sentTo(call: Promise<unknown>): Promise<string | null> {
  try {
    await call;
    return null;
  } catch (thrown) {
    const digest = (thrown as { digest?: unknown } | null)?.digest;
    if (typeof digest !== 'string' || !digest.startsWith('NEXT_REDIRECT;')) throw thrown;
    return digest.split(';')[2] ?? null;
  }
}

function visibleText(markup: string): string {
  return [...markup.matchAll(/>([^<>]+)</g)].map((m) => (m[1] ?? '').trim()).filter(Boolean).join(' ');
}

/** The sessions that lack every role of `row`, as real register sessions. */
function lacking(row: ScreenEntry): readonly (readonly Role[])[] {
  const all: readonly (readonly Role[])[] = [[], ['expert'], ['admin'], ['expert', 'admin']];
  return all.filter((roles) => row.roles !== 'any' && !row.roles.some((role) => roles.includes(role)));
}

beforeEach(() => {
  forgetEverySession();
  jar.value = null;
});

describe('8 (fixture): /403 for every role-gated row names the role the registry requires', () => {
  for (const row of GATED) {
    it(`${row.address} (${(row.roles as readonly Role[]).join(' | ')})`, async () => {
      const sessions = lacking(row);
      expect(sessions.length, 'a role-gated row has at least the empty role set lacking it').toBeGreaterThan(0);
      for (const roles of sessions) {
        forgetEverySession();
        jar.value = openSession({ ...COMPLETE, roles: [...roles] }, 'qa-credential', 3600);
        const { path, params } = concrete(row);
        const location = await sentTo(
          enforceScreen(row, { params: Promise.resolve(params), searchParams: Promise.resolve({ ...PROPS_QUERY }) }),
        );
        expect(location, `roles [${roles.join(',')}] on ${row.address}`).toBe(
          `/403?from=${encodeURIComponent(`${path}?tab=all`)}`,
        );
        const from = new URL(location as string, 'http://qa.invalid').searchParams.get('from');
        const required = requiredRolesFor(from, FIXTURE);
        expect(required).toEqual(row.roles);
        const text = visibleText(renderScreen(newClient(), createElement(ForbiddenPage, { requiredRoles: required })));
        for (const role of row.roles as readonly Role[]) {
          expect(text, `the /403 screen for ${row.address}`).toContain(`«${ROLE_LABELS[role]}»`);
        }
        // And it names no role the row does not require.
        for (const role of Object.keys(ROLE_LABELS) as Role[]) {
          if (!(row.roles as readonly Role[]).includes(role)) expect(text).not.toContain(`«${ROLE_LABELS[role]}»`);
        }
      }
    });
  }

  it('a session holding one of the roles is let through', async () => {
    for (const row of GATED) {
      for (const role of row.roles as readonly Role[]) {
        forgetEverySession();
        jar.value = openSession({ ...COMPLETE, roles: [role] }, 'qa-credential', 3600);
        const { params } = concrete(row);
        expect(await sentTo(enforceScreen(row, { params: Promise.resolve(params), searchParams: Promise.resolve({}) }))).toBeNull();
      }
    }
  });
});

describe('8 (live): every live row is role-free, so the /403 route names no role for any of them', () => {
  it('the real /403 route, given each live row as from, renders the screen with no role named', async () => {
    const live = SCREEN_REGISTRY.filter((row) => row.address !== '/403');
    expect(live.length).toBeGreaterThan(20);
    for (const row of live) {
      const { path } = concrete(row);
      const element = await ForbiddenRoute({ params: Promise.resolve({}), searchParams: Promise.resolve({ from: path }) });
      const text = visibleText(renderScreen(newClient(), element));
      expect(text, row.address).toContain('Доступ закрыт');
      for (const label of Object.values(ROLE_LABELS)) expect(text, row.address).not.toContain(`«${label}»`);
    }
  });
});
