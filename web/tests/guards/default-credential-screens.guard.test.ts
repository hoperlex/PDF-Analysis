/**
 * Guard: `R-50`'s screen half — **every screen but three is behind the default-credential
 * lock**, and the three that are not are named here with the reason each one is open.
 *
 * ## Why a sweep and not a test per screen
 *
 * The ruling is a statement about the *set* of screens: "a sign-in on a default credential
 * lands on `/account/password` and no other screen opens." A test per screen is a list of
 * the screens somebody remembered, and `D-88` is this repository's own record of what that
 * costs — four screens were added, an English sentence was put on each, and the whole
 * frontend suite stayed green because every instrument's subject was a hand-written list.
 *
 * So the subject is derived: `routeAddresses()` walks `web/src/app` for `page.tsx` exactly
 * as `tests/e2e/test_pc01_journey_conformance.py` does. A new screen is behind the lock, or
 * it is written into {@link OPEN_TO_A_DEFAULT_CREDENTIAL} by somebody who has decided it
 * should be open and said why. There is no third place for it to be, and a new `page.tsx`
 * that does neither is red here **naming its address**.
 *
 * ## Why it reads the source rather than driving the route
 *
 * Driving would be better and is not available: `redirect()` is Next's own control flow and
 * the register lives in the module the route imports, so a driven route would need the
 * framework's request context around it. What is checked instead is the one thing a static
 * read can check honestly — that the call is *there* — plus, in the second half of this
 * file, that the function it names really redirects, driven for real against the register.
 * Neither half is sufficient alone: the first would pass over a lock that does nothing, the
 * second would pass over a screen that never calls it.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, it, vi } from 'vitest';

import { REPO_ROOT } from './lib/repo';
import { routeAddresses } from '../unit/screens/route-screens';

import { forgetEverySession, openSession } from '@/app/bff/session/store';

/*
 * The cookie jar the lock reads. Set by each case; `null` is a browser with no session.
 */
const jar = vi.hoisted(() => ({ value: null as string | null }));

vi.mock('next/headers', () => ({
  cookies: async () => ({
    get: (name: string) => (jar.value === null ? undefined : { name, value: jar.value }),
  }),
}));

const { requireAChangedPassword, CHANGE_PASSWORD_SCREEN } = await import(
  '@/app/bff/session/screen-lock'
);

/** The call each guarded route file must make. Named as text, because that is what is read. */
const THE_CALL = 'requireAChangedPassword()';

/**
 * The addresses a credential still on the seeded password may open, and why each is open.
 *
 * A register and not a rule: "anything under `/account`" would open the next screen
 * somebody put there without anybody deciding to. Each entry is a decision.
 */
const OPEN_TO_A_DEFAULT_CREDENTIAL: ReadonlyMap<string, string> = new Map([
  [
    '/account/password',
    'the way out. A lock on this screen would be a deployment in which the only way to ' +
      'satisfy the condition is barred by the condition.',
  ],
  [
    '/login',
    'the way in, and the way out of the session altogether. It renders the sign-out panel ' +
      'when a session is open, so locking it would trap a reviewer inside a session they ' +
      'cannot use and cannot leave.',
  ],
  [
    '/',
    'renders nothing at all: its whole body is `redirect("/projects")`, and /projects is ' +
      'locked. A second lock here would refuse the same reviewer one address earlier and ' +
      'tell them nothing extra.',
  ],
]);

/**
 * The route file's CODE, with its comments removed.
 *
 * Measured, not guessed: the first run of this guard reported `/account/password` as both
 * locked and registered open, because its docstring says *"it does not call
 * `requireAChangedPassword()`"* — which is exactly the sentence a registered-open screen
 * ought to carry. A guard that reads prose as code makes a file's explanation of itself
 * into evidence about itself.
 */
function codeOf(file: string): string {
  return readFileSync(join(REPO_ROOT, file), 'utf8')
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .replace(/(^|[^:])\/\/[^\n]*/g, '$1 ');
}

describe('R-50: every screen is behind the lock, or is named as open', () => {
  it('the comment strip leaves code and removes prose, so neither is read as the other', () => {
    // Both halves, because a strip that removed everything would make every screen look
    // unlocked and a strip that removed nothing would make the open register look locked.
    const open = codeOf('web/src/app/account/password/page.tsx');
    expect(open).not.toContain(THE_CALL);
    expect(open).toContain('ChangePasswordPage');
    const locked = codeOf('web/src/app/dashboard/page.tsx');
    expect(locked).toContain(THE_CALL);
  });

  it('the derivation reaches the route tree at all', () => {
    const addresses = routeAddresses().map((route) => route.address);
    expect(addresses.length).toBeGreaterThanOrEqual(16);
    expect(addresses).toContain('/dashboard');
    expect(addresses).toContain('/account/password');
  });

  it('each address either calls the lock or is registered as open, and never both', () => {
    const missing: string[] = [];
    const both: string[] = [];
    for (const { address, file } of routeAddresses()) {
      const calls = codeOf(file).includes(THE_CALL);
      const open = OPEN_TO_A_DEFAULT_CREDENTIAL.has(address);
      if (!calls && !open) missing.push(`${address} (${file})`);
      if (calls && open) both.push(`${address} (${file})`);
    }
    expect(missing,
      `these screens open to a credential still on the deployment's seeded password. Add ` +
        `\`await ${THE_CALL}\` to the route, or register the address in ` +
        `OPEN_TO_A_DEFAULT_CREDENTIAL with the reason it is open`,
    ).toEqual([]);
    expect(both, 'a registered-open screen must not also lock itself').toEqual([]);
  });

  it('the register names only addresses that exist', () => {
    const addresses = new Set(routeAddresses().map((route) => route.address));
    for (const address of OPEN_TO_A_DEFAULT_CREDENTIAL.keys()) {
      expect(addresses, `${address} is registered as open and is not a route`).toContain(
        address,
      );
    }
  });

  it('every reason is written down, so the register cannot grow silently', () => {
    for (const [address, reason] of OPEN_TO_A_DEFAULT_CREDENTIAL) {
      expect(reason.length, `${address} is registered with no reason`).toBeGreaterThan(40);
    }
  });
});

describe('R-50: the lock itself, driven against the register', () => {
  it('redirects a session on a default credential to the change screen', async () => {
    forgetEverySession();
    jar.value = openSession('проверяющий', 'a-credential', 3600, true);
    await expect(requireAChangedPassword()).rejects.toThrow(/NEXT_REDIRECT/);
  });

  it('names the change screen and no other address in the redirect', async () => {
    forgetEverySession();
    jar.value = openSession('проверяющий', 'a-credential', 3600, true);
    const thrown = await requireAChangedPassword().then(
      () => null,
      (error: unknown) => String((error as { digest?: unknown }).digest ?? error),
    );
    expect(thrown).toContain(CHANGE_PASSWORD_SCREEN);
  });

  it('lets a session whose password has been changed through', async () => {
    forgetEverySession();
    jar.value = openSession('проверяющий', 'a-credential', 3600, false);
    await expect(requireAChangedPassword()).resolves.toBeUndefined();
  });

  it('lets a browser with no session through, because there is nothing to lock', async () => {
    forgetEverySession();
    jar.value = null;
    await expect(requireAChangedPassword()).resolves.toBeUndefined();
    jar.value = '0'.repeat(64);
    await expect(requireAChangedPassword()).resolves.toBeUndefined();
  });
});
