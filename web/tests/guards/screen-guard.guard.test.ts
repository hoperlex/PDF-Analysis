/**
 * Guard: `W50-PLAN.md` §3.2 — **every screen calls `requireScreen` with its own address and
 * its own props, and the guard decides the five things it decides, in order.**
 *
 * Was `default-credential-screens.guard.test.ts`, `R-50`'s sweep over
 * `requireAChangedPassword()`. That function decided one of these five things and kept a
 * register of three addresses that skipped it; the screen registry now says, row by row, who
 * may open each address, so there is no second register here and no screen skips the call.
 *
 * ## Why a sweep and not a test per screen
 *
 * The rule is a statement about the *set* of screens. A test per screen is a list of the
 * screens somebody remembered, and `D-88` is this repository's own record of what that
 * costs. So the subject is derived: `routeAddresses()` walks `web/src/app` for `page.tsx`
 * exactly as `tests/e2e/test_pc01_journey_conformance.py` does, and a route file that does
 * not make the call — or makes it with another screen's address, or without the props Next
 * handed it — is red here **naming its address**.
 *
 * ## Why it reads the source AND drives the guard
 *
 * The first half reads the route files, because that is the one thing a static read checks
 * honestly: that the call is *there*, with the right address. The second half drives the
 * function the call names against the real session register — `openSession` with a full
 * subject — through each of the five decisions, so a guard that decided nothing would be
 * red there. Neither half is sufficient alone.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { createElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { REPO_ROOT, WEB_ROOT, readText, walkFiles } from './lib/repo';
import { newClient, renderScreen } from '../unit/screens/harness';
import { routeAddresses } from '../unit/screens/route-screens';

import type { SessionAccount } from '@/app/bff/session/store';
import { closeSession, forgetEverySession, openSession } from '@/app/bff/session/store';
import type { Role } from '@/shared/api';
import type { ScreenEntry } from '@/shared/config';
import { SCREEN_REGISTRY, screenMatching } from '@/shared/config';

/*
 * The cookie jar the guard reads. Set by each case; `null` is a browser with no session.
 */
const jar = vi.hoisted(() => ({ value: null as string | null }));

vi.mock('next/headers', () => ({
  cookies: async () => ({
    get: (name: string) => (jar.value === null ? undefined : { name, value: jar.value }),
  }),
}));

const screenLock = await import('@/app/bff/session/screen-lock');
const { default: ErrorBoundary } = await import('@/app/error');
const { requireScreen, enforceScreen } = screenLock;

// ================================================================= the static half

/** Comments removed, so a file's explanation of itself is not read as its code. */
function stripComments(text: string): string {
  return text.replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/(^|[^:])\/\/[^\n]*/g, '$1 ');
}

function codeOf(file: string): string {
  return stripComments(readFileSync(join(REPO_ROOT, file), 'utf8'));
}

/** Every `requireScreen(` call in a route's code, with the address literal it names. */
const ANY_CALL = /requireScreen\s*(?:<[^>]*>)?\(\s*(?:'([^']*)'|"([^"]*)"|([^,)]*))/g;

/**
 * What is wrong with one route file's guard call, as sentences naming its address. Empty
 * when the file awaits exactly one `requireScreen('<its own address>', { params,
 * searchParams })` before it returns anything.
 */
function guardFindings(address: string, code: string): string[] {
  const calls = [...code.matchAll(ANY_CALL)];
  if (calls.length === 0) return [`${address} does not call requireScreen`];
  const findings: string[] = [];
  if (calls.length > 1) findings.push(`${address} calls requireScreen ${calls.length} times`);
  for (const call of calls) {
    const named = call[1] ?? call[2] ?? null;
    if (named !== address) {
      findings.push(`${address} calls requireScreen with ${named === null ? 'no address literal' : named}`);
    }
  }
  const exact = new RegExp(
    `await\\s+requireScreen\\(\\s*'${address.replace(/[.*+?^${}()|[\]\\/]/g, '\\$&')}'\\s*,\\s*\\{\\s*params\\s*,\\s*searchParams\\s*\\}\\s*\\)`,
  );
  const awaited = exact.exec(code);
  if (awaited === null) {
    findings.push(`${address} does not await requireScreen('${address}', { params, searchParams })`);
  } else {
    const firstReturn = code.indexOf('return');
    if (firstReturn !== -1 && firstReturn < awaited.index) {
      findings.push(`${address} returns before it awaits requireScreen`);
    }
  }
  return findings;
}

describe('W50: every screen awaits requireScreen with its own address and props', () => {
  it('the comment strip leaves code and removes prose, so neither is read as the other', () => {
    const text =
      "/** await requireScreen('/x', { params, searchParams }) */\n" +
      "// await requireScreen('/x', { params, searchParams })\n" +
      'const kept = 1;';
    expect(stripComments(text)).not.toContain('requireScreen');
    expect(stripComments(text)).toContain('const kept = 1;');
    // And on a real route file: the code keeps its call.
    expect(codeOf('web/src/app/dashboard/page.tsx')).toContain("requireScreen('/dashboard'");
  });

  it('the derivation reaches the route tree at all', () => {
    const addresses = routeAddresses().map((route) => route.address);
    expect(addresses.length).toBeGreaterThanOrEqual(22);
    expect(addresses).toContain('/dashboard');
    expect(addresses).toContain('/account/password');
    expect(addresses).toContain('/403');
  });

  it('can fail: a route with no call, another address, no props, or a call after rendering', () => {
    expect(guardFindings('/x', 'export default function X() { return null; }')).toEqual([
      '/x does not call requireScreen',
    ]);
    expect(
      guardFindings('/x', "await requireScreen('/y', { params, searchParams }); return null;"),
    ).toEqual([
      '/x calls requireScreen with /y',
      "/x does not await requireScreen('/x', { params, searchParams })",
    ]);
    expect(guardFindings('/x', "await requireScreen('/x', {}); return null;")).toEqual([
      "/x does not await requireScreen('/x', { params, searchParams })",
    ]);
    expect(
      guardFindings('/x', "return null; await requireScreen('/x', { params, searchParams });"),
    ).toEqual(['/x returns before it awaits requireScreen']);
    expect(
      guardFindings('/x', "await requireScreen('/x', { params, searchParams }); return null;"),
    ).toEqual([]);
  });

  it('every route file awaits requireScreen with its own address and its own props', () => {
    const findings = routeAddresses().flatMap(({ address, file }) =>
      guardFindings(address, codeOf(file)).map((finding) => `${finding} (${file})`),
    );
    expect(
      findings,
      'these screens are not behind the guard as W50-PLAN.md §3.2 requires. Each page.tsx ' +
        "awaits requireScreen('<its own address>', { params, searchParams }) before it renders",
    ).toEqual([]);
  });

  it('the old lock is gone: no module defines or calls requireAChangedPassword', () => {
    expect('requireAChangedPassword' in screenLock).toBe(false);
    const offenders = walkFiles(join(WEB_ROOT, 'src'), (path) => /\.(?:ts|tsx)$/.test(path)).filter(
      (path) => stripComments(readText(path)).includes('requireAChangedPassword'),
    );
    expect(offenders).toEqual([]);
  });
});

// ================================================================= the driven half

const COMPLETE: SessionAccount = {
  login: 'petrova@example.org',
  displayLabel: 'Петрова А. С.',
  initials: 'ПА',
  roles: ['expert'],
  isDefaultCredential: false,
  profileComplete: true,
};

/** Open a real session in the register for `changes` over a complete account, and hold its cookie. */
function signIn(changes: Partial<SessionAccount> = {}): string {
  const id = openSession({ ...COMPLETE, ...changes }, 'a-credential', 3600);
  jar.value = id;
  return id;
}

/** Page props as Next hands them. */
function props(params: Record<string, string> = {}, query: Record<string, string | string[]> = {}) {
  return { params: Promise.resolve(params), searchParams: Promise.resolve(query) };
}

/** Where a guard call sent the browser, or `null` when it returned normally. */
async function sentTo(call: Promise<unknown>): Promise<string | null> {
  try {
    await call;
    return null;
  } catch (thrown) {
    const digest = (thrown as { digest?: unknown })?.digest;
    if (typeof digest !== 'string' || !digest.startsWith('NEXT_REDIRECT;')) throw thrown;
    // `NEXT_REDIRECT;<replace|push>;<url>;<status>;`
    return digest.split(';')[2] ?? null;
  }
}

const A_PROJECT = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';

/** A synthetic role-gated row keeps the mechanism control independent of live registry data. */
const ADMIN_USERS: ScreenEntry = {
  address: '/admin/users',
  label: 'Учётные записи',
  group: 'admin',
  access: 'session',
  roles: ['admin'],
  inMenu: true,
};

beforeEach(() => {
  forgetEverySession();
  jar.value = null;
});

describe('decision 1: a guest is sent to sign in, carrying the address it asked for', () => {
  it('on a session screen, with the path and its query in next', async () => {
    expect(await sentTo(requireScreen('/projects', props({}, { x: '1' })))).toBe(
      `/login?next=${encodeURIComponent('/projects?x=1')}`,
    );
  });

  it('on a dynamic screen, with the concrete address, not the template', async () => {
    expect(
      await sentTo(requireScreen('/projects/[project_uid]', props({ project_uid: A_PROJECT }))),
    ).toBe(`/login?next=${encodeURIComponent(`/projects/${A_PROJECT}`)}`);
  });

  it('on a screen open to a default credential too: it still needs a session', async () => {
    expect(await sentTo(requireScreen('/account/password', props()))).toBe(
      `/login?next=${encodeURIComponent('/account/password')}`,
    );
  });

  it('drops an address too long to carry rather than cutting it or echoing it', async () => {
    const long = 'я'.repeat(200);
    expect(await sentTo(requireScreen('/projects', props({}, { q: long })))).toBe('/login');
  });

  it('lets a guest open a public screen, and returns no subject', async () => {
    expect(await requireScreen('/login', props())).toBeNull();
    expect(await requireScreen('/register', props())).toBeNull();
    expect(await requireScreen('/register/submitted', props())).toBeNull();
    expect(await requireScreen('/403', props())).toBeNull();
  });

  it('reads a cookie the register does not hold, and a closed session, as no session', async () => {
    jar.value = '0'.repeat(64);
    expect(await sentTo(requireScreen('/projects', props()))).toBe(
      `/login?next=${encodeURIComponent('/projects')}`,
    );
    const id = signIn();
    closeSession(id); // what the BFF does on an upstream 401
    expect(await sentTo(requireScreen('/projects', props()))).toBe(
      `/login?next=${encodeURIComponent('/projects')}`,
    );
  });
});

describe('decision 2: a default credential opens only the screens that change it', () => {
  it('is sent from a session screen to the change screen', async () => {
    signIn({ isDefaultCredential: true });
    expect(await sentTo(requireScreen('/projects', props()))).toBe('/account/password');
    expect(await sentTo(requireScreen('/', props()))).toBe('/account/password');
  });

  it('opens the change screen and the profile, which are open to it', async () => {
    signIn({ isDefaultCredential: true });
    expect((await requireScreen('/account/password', props())).isDefaultCredential).toBe(true);
    expect(await sentTo(requireScreen('/account', props()))).toBeNull();
  });

  it('comes before the profile: a default credential with no profile changes the password first', async () => {
    signIn({ isDefaultCredential: true, profileComplete: false });
    expect(await sentTo(requireScreen('/projects', props()))).toBe('/account/password');
  });
});

describe('decision 3: an incomplete profile opens only the screens that complete it', () => {
  it('is sent from a session screen to /account', async () => {
    signIn({ profileComplete: false });
    expect(await sentTo(requireScreen('/projects', props()))).toBe('/account');
    expect(await sentTo(requireScreen('/dashboard', props()))).toBe('/account');
  });

  it('opens /account and the change screen', async () => {
    signIn({ profileComplete: false });
    expect((await requireScreen('/account', props())).profileComplete).toBe(false);
    expect(await sentTo(requireScreen('/account/password', props()))).toBeNull();
  });
});

describe('decision 4: a session lacking every role a screen lists is sent to /403', () => {
  const liveAdmin = [
    ['/admin/users', {}],
    ['/admin/users/[user_uid]', { user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F' }],
    ['/admin/registrations', {}],
  ] as const;

  it('applies the live admin rows to expert, empty, unknown and admin sessions', async () => {
    for (const [address, params] of liveAdmin) {
      for (const roles of [['expert'], [], ['superuser']] as const) {
        signIn({ roles: [...roles] as Role[] });
        const concrete = address.replace('[user_uid]', 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F');
        expect(await sentTo(requireScreen(address, props(params))), `${address}: ${roles.join(',')}`).toBe(
          `/403?from=${encodeURIComponent(concrete)}`,
        );
      }
      signIn({ roles: ['admin'] });
      expect(await sentTo(requireScreen(address, props(params))), address).toBeNull();
    }
  });

  it('sends an expert from an administrator screen, carrying where it was going in from', async () => {
    signIn({ roles: ['expert'] });
    expect(await sentTo(enforceScreen(ADMIN_USERS, props()))).toBe(
      `/403?from=${encodeURIComponent('/admin/users')}`,
    );
  });

  it('lets a holder of any one listed role through', async () => {
    signIn({ roles: ['expert', 'admin'] });
    expect(await sentTo(enforceScreen(ADMIN_USERS, props()))).toBeNull();
  });

  it('sends an empty role set, and never reads an unknown role as any', async () => {
    signIn({ roles: [] });
    expect(await sentTo(enforceScreen(ADMIN_USERS, props()))).toBe(
      `/403?from=${encodeURIComponent('/admin/users')}`,
    );
    signIn({ roles: ['superuser' as Role] });
    expect(await sentTo(enforceScreen(ADMIN_USERS, props()))).toBe(
      `/403?from=${encodeURIComponent('/admin/users')}`,
    );
  });

  it('asks nothing of a row that lists no role: every W50 screen admits an empty role set', async () => {
    signIn({ roles: [] });
    expect(await sentTo(requireScreen('/projects', props()))).toBeNull();
  });
});

describe('decision 5: a session has nothing to do on the sign-in screen', () => {
  it('sends a signed-in visit to /login to /', async () => {
    signIn();
    expect(await sentTo(requireScreen('/login', props()))).toBe('/');
    expect(await sentTo(requireScreen('/login', props({}, { next: '/projects' })))).toBe('/');
  });
});

describe('a normal return hands the route the subject, and nothing else', () => {
  it('returns the session subject on a screen the session may open, without its credential', async () => {
    signIn();
    const subject = await requireScreen('/projects', props());
    expect(subject).toEqual(COMPLETE);
    expect(JSON.stringify(subject)).not.toContain('a-credential');
  });
});

describe('no redirect cycle: every chain of decisions ends on a screen that renders', () => {
  const KINDS: Record<string, Partial<SessionAccount> | null> = {
    guest: null,
    complete: {},
    'default credential': { isDefaultCredential: true },
    'incomplete profile': { profileComplete: false },
    'default and incomplete': { isDefaultCredential: true, profileComplete: false },
    'no roles': { roles: [] },
  };

  for (const [kind, changes] of Object.entries(KINDS)) {
    it(`${kind}: from every registered address, in at most three hops`, async () => {
      for (const screen of SCREEN_REGISTRY) {
        forgetEverySession();
        jar.value = null;
        if (changes !== null) signIn(changes);
        let address: string = screen.address.replace(/\[[^\]]+\]/g, A_PROJECT);
        let hops = 0;
        for (;;) {
          const path = address.split('?')[0] as string;
          const row = screenMatching(path);
          expect(row, `${kind}: ${screen.address} sent the browser to ${address}, which is no screen`).toBeDefined();
          const params = Object.fromEntries(
            [...(row as ScreenEntry).address.matchAll(/\[([^\]]+)\]/g)].map((m) => [m[1] as string, A_PROJECT]),
          );
          const next = await sentTo(enforceScreen(row as ScreenEntry, props(params)));
          if (next === null) break;
          address = next;
          hops += 1;
          expect(hops, `${kind}: ${screen.address} is still redirecting after ${hops} hops`).toBeLessThanOrEqual(3);
        }
      }
    });
  }
});

// ======================================================= §3.3: the screens around the guard

/** The text nodes a reader would see, decoded. Attributes are machinery and are not read. */
function visibleText(markup: string): string[] {
  return [...markup.matchAll(/>([^<>]+)</g)]
    .map((m) => (m[1] ?? '').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&').trim())
    .filter((text) => text.length > 0);
}

describe('§3.3: the error boundaries are typed states, Russian, with no raw error', () => {
  it('the error boundary shows none of what was thrown, and says what a reader can do', () => {
    const thrown = Object.assign(
      new TypeError("Cannot read properties of undefined (reading 'items') at /srv/web/.next/server/app.js"),
      { digest: '3141592653' },
    );
    const markup = renderScreen(newClient(), createElement(ErrorBoundary, { error: thrown, reset: () => {} }));
    const text = visibleText(markup).join('\n');
    expect(markup).toContain('am-state--error');
    expect(text).toContain('При построении экрана произошла ошибка.');
    expect(text).toContain('Открыть ещё раз');
    for (const leaked of ['Cannot read', 'TypeError', '/srv/web', 'items']) {
      expect(markup, `the boundary rendered ${leaked}`).not.toContain(leaked);
    }
    // The digest is the one thing an operator can trace, and it is an opaque number.
    expect(text).toContain('3141592653');
    expect(text.replace(/3141592653/g, ''), 'the boundary rendered a Latin word').not.toMatch(/[A-Za-z]{2,}/);
  });

  it('can fail: the reading finds an English word and a leaked message', () => {
    const markup = '<p class="am-state__title">Something went wrong</p>';
    expect(visibleText(markup).join('\n')).toMatch(/[A-Za-z]{2,}/);
  });
});
