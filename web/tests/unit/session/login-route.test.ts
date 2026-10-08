/**
 * `/login` — the route file, which is three reads and a delegation.
 *
 * Worth its own file for the reason `tests/unit/screens/routes.test.ts` gives about the
 * other five: a route that handed the wrong value to a prop would type-check and render a
 * screen that says the wrong thing about who is signed in. The addition here is a second
 * property the other routes have no equivalent of — **the props this route passes down
 * carry no credential.** Anything a server component passes to a page becomes bytes in the
 * RSC payload, which is bytes the browser holds, so the shape of that object is asserted.
 */

import { describe, expect, it, vi } from 'vitest';

import { SignInPage } from '@/_pages/sign-in';
import { forgetEverySession, openSession } from '@/app/bff/session/store';

const jar = vi.hoisted(() => ({ value: null as string | null }));

vi.mock('next/headers', () => ({
  cookies: async () => ({
    get: (name: string) => (jar.value === null ? undefined : { name, value: jar.value }),
  }),
}));

const { default: LoginRoute } = await import('@/app/login/page');

const MINTED = 'minted-token-the-screen-must-never-see';

function query(params: Record<string, string | string[]> = {}) {
  return { searchParams: Promise.resolve(params) };
}

describe('the route tells the screen who is signed in, and nothing more', () => {
  it('renders the credentials form when the browser carries no cookie', async () => {
    forgetEverySession();
    jar.value = null;
    const element = await LoginRoute(query());
    expect(element.type).toBe(SignInPage);
    expect(element.props).toEqual({ login: null, refusal: null, unknownRefusal: false, next: null });
  });

  it('sends a live session to /, rendering nothing (W50-PLAN.md §3.2, decision five)', async () => {
    forgetEverySession();
    jar.value = openSession(
      {
        login: 'проверяющий',
        displayLabel: 'Проверяющая А. Б.',
        initials: 'ПА',
        roles: ['expert'],
        isDefaultCredential: false,
        profileComplete: true,
      },
      MINTED,
      3600,
    );
    // Until W50 this route named the reviewer and rendered the sign-out panel; the frame
    // carries the way out now, and the sign-in screen has nothing to offer a session. The
    // redirect is the whole answer, so no payload -- and no credential -- is produced.
    const thrown = await LoginRoute(query({ next: '/projects' })).then(
      () => null,
      (error: unknown) => String((error as { digest?: unknown }).digest ?? error),
    );
    expect(thrown).toMatch(/^NEXT_REDIRECT;[a-z]+;\/;/);
    expect(thrown).not.toContain(MINTED);
  });

  it('treats a cookie that names no session as no session', async () => {
    forgetEverySession();
    jar.value = '0'.repeat(64);
    const element = await LoginRoute(query());
    expect(element.props).toEqual({ login: null, refusal: null, unknownRefusal: false, next: null });
  });

  it('renders only a refusal the feature publishes, whatever the query string says', async () => {
    forgetEverySession();
    jar.value = null;
    expect((await LoginRoute(query({ refusal: 'credentials' }))).props).toEqual({
      login: null,
      refusal: 'credentials',
      unknownRefusal: false,
      next: null,
    });
    // The two values `W49-BFF-01` added reach the screen like the other four.
    for (const added of ['pending', 'throttled']) {
      expect((await LoginRoute(query({ refusal: added }))).props.refusal).toBe(added);
    }
    // A hand-typed or injected value does not become a known refusal.
    for (const hostile of ['boom', '<script>', '', 'CREDENTIALS']) {
      const props = (await LoginRoute(query({ refusal: hostile }))).props;
      expect(props.refusal).toBeNull();
      expect(props.unknownRefusal).toBe(true);
    }
    // A repeated parameter arrives as an array; the first is read and still validated.
    expect((await LoginRoute(query({ refusal: ['upstream', 'boom'] }))).props.refusal).toBe(
      'upstream',
    );
    expect((await LoginRoute(query({ refusal: ['boom'] }))).props.refusal).toBeNull();
  });

  it('hands the form a next the registry accepts, and drops every other', async () => {
    forgetEverySession();
    jar.value = null;
    expect((await LoginRoute(query({ next: '/projects?x=1' }))).props.next).toBe('/projects?x=1');
    for (const hostile of ['//evil.example', 'https://evil.example', '/\\evil', '/nowhere', '']) {
      expect((await LoginRoute(query({ next: hostile }))).props.next).toBeNull();
    }
    expect((await LoginRoute(query({ next: ['/dashboard', '//evil.example'] }))).props.next).toBe(
      '/dashboard',
    );
  });

  it('works when Next hands it no query at all', async () => {
    forgetEverySession();
    jar.value = null;
    const element = await LoginRoute({});
    expect(element.props).toEqual({ login: null, refusal: null, unknownRefusal: false, next: null });
  });
});
