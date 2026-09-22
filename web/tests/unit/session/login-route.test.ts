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
    expect(element.props).toEqual({ login: null, refusal: null });
  });

  it('names the reviewer when the cookie points at a live session', async () => {
    forgetEverySession();
    jar.value = openSession('проверяющий', MINTED, 3600);
    const element = await LoginRoute(query());
    expect(element.props).toEqual({ login: 'проверяющий', refusal: null });
    // The one assertion this route exists to make: no credential reaches the payload.
    expect(JSON.stringify(element.props)).not.toContain(MINTED);
  });

  it('treats a cookie that names no session as no session', async () => {
    forgetEverySession();
    jar.value = '0'.repeat(64);
    const element = await LoginRoute(query());
    expect(element.props).toEqual({ login: null, refusal: null });
  });

  it('renders only a refusal the feature publishes, whatever the query string says', async () => {
    forgetEverySession();
    jar.value = null;
    expect((await LoginRoute(query({ refusal: 'credentials' }))).props).toEqual({
      login: null,
      refusal: 'credentials',
    });
    // A hand-typed or injected value renders no sentence at all.
    for (const hostile of ['boom', '<script>', '', 'CREDENTIALS']) {
      expect((await LoginRoute(query({ refusal: hostile }))).props.refusal).toBeNull();
    }
    // A repeated parameter arrives as an array; the first is read and still validated.
    expect((await LoginRoute(query({ refusal: ['upstream', 'boom'] }))).props.refusal).toBe(
      'upstream',
    );
    expect((await LoginRoute(query({ refusal: ['boom'] }))).props.refusal).toBeNull();
  });

  it('works when Next hands it no query at all', async () => {
    forgetEverySession();
    jar.value = null;
    const element = await LoginRoute({});
    expect(element.props).toEqual({ login: null, refusal: null });
  });
});
