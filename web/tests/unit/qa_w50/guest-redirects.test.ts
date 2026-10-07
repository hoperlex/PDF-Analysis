/**
 * `W50-QA-01`, item 5 — a guest is sent from every registered `session` screen to
 * `/login?next=<that concrete path and query>`, and the `next` it carries survives the way back.
 *
 * `W50-PLAN.md` §3.2, decision 1: "no session and `access !== 'public'` →
 * `redirect('/login?next=<validated>')`, where `next` is the concrete path plus its query
 * string." The subject is every row of the live registry whose access is `session`, derived —
 * not listed — and each is driven through **its own route file** (`web/src/app/**\/page.tsx`,
 * found by walking the tree), so a route that passed the wrong address, dropped its `params`
 * or forgot its `searchParams` is red here naming its address. Dynamic segments are filled with
 * well-formed identifiers of the contract's own shapes (`prj_`/`doc_`/`ver_`/`run_` + a ULID),
 * each a different value, so a route that crossed two segments is red too.
 *
 * "Guest" is read against the real session register (`@/app/bff/session/store`): no cookie at
 * all, and a well-formed cookie the register does not hold.
 *
 * The way back is the second half: the `next` the guard produced must pass the registry's one
 * validator unchanged (the BFF validates it again before its after-sign-in redirect), and the
 * sign-in screen a guest lands on must carry it in its hidden field.
 *
 * Written by QA from the plan, without the lane reports.
 */

import { readdirSync, statSync } from 'node:fs';
import { join, relative, sep } from 'node:path';

import { beforeEach, describe, expect, it, vi } from 'vitest';

import { WEB_ROOT } from '../../guards/lib/repo';
import { newClient, renderScreen } from '../screens/harness';

import { forgetEverySession } from '@/app/bff/session/store';
import { SIGN_IN_NEXT_FIELD } from '@/features/sign-in';
import { SCREEN_REGISTRY, safeReturnPath } from '@/shared/config';

const jar = vi.hoisted(() => ({ value: null as string | null }));

vi.mock('next/headers', () => ({
  cookies: async () => ({
    get: (name: string) => (jar.value === null ? undefined : { name, value: jar.value }),
  }),
}));

const { default: LoginRoute } = await import('@/app/login/page');

// ------------------------------------------------------------------ the route tree, walked

const APP_ROOT = join(WEB_ROOT, 'src', 'app');

/** Every `page.tsx` under `web/src/app`, by the address it serves. Route groups `(x)` are not addresses. */
function pageFiles(): Map<string, string> {
  const found = new Map<string, string>();
  const walk = (dir: string): void => {
    for (const name of readdirSync(dir)) {
      const path = join(dir, name);
      if (statSync(path).isDirectory()) walk(path);
      else if (name === 'page.tsx') {
        const parts = relative(APP_ROOT, dir)
          .split(sep)
          .filter((part) => part.length > 0 && !/^\(.*\)$/.test(part));
        found.set(`/${parts.join('/')}`, path);
      }
    }
  };
  walk(APP_ROOT);
  return found;
}

type RouteProps = {
  readonly params: Promise<Record<string, string>>;
  readonly searchParams: Promise<Record<string, string | string[]>>;
};
type Route = (props: RouteProps) => Promise<unknown>;

async function routeAt(address: string): Promise<Route> {
  const file = pageFiles().get(address);
  if (file === undefined) throw new Error(`no page.tsx serves the registered address ${address}`);
  const module = (await import(/* @vite-ignore */ file)) as { default: Route };
  return module.default;
}

// --------------------------------------------------------- well-formed, distinct identifiers

/** The contract's identity shapes: `<prefix>_<26 Crockford base-32>`. One value per segment name. */
const IDENTIFIERS: Readonly<Record<string, string>> = {
  project_uid: 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8A',
  document_uid: 'doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8C',
  version_uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8D',
  run_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8E',
};

function segmentsOf(template: string): string[] {
  return [...template.matchAll(/\[([^\]]+)\]/g)].map((match) => match[1] as string);
}

function filled(template: string): { readonly path: string; readonly params: Record<string, string> } {
  const params: Record<string, string> = {};
  for (const name of segmentsOf(template)) {
    const value = IDENTIFIERS[name];
    if (value === undefined) throw new Error(`QA has no well-formed identifier for the segment [${name}] of ${template}`);
    params[name] = value;
  }
  const path = template.replace(/\[([^\]]+)\]/g, (_, name: string) => params[name] as string);
  return { path, params };
}

// ------------------------------------------------------------------------ the redirect read

/** Where a route sent the browser, or `null` when it rendered. */
async function sentTo(call: Promise<unknown>): Promise<string | null> {
  try {
    await call;
    return null;
  } catch (thrown) {
    const digest = (thrown as { digest?: unknown } | null)?.digest;
    if (typeof digest !== 'string' || !digest.startsWith('NEXT_REDIRECT;')) throw thrown;
    // `NEXT_REDIRECT;<replace|push>;<url>;<status>;`
    return digest.split(';')[2] ?? null;
  }
}

const SESSION_ROWS = SCREEN_REGISTRY.filter((row) => row.access === 'session');
const NON_PUBLIC_ROWS = SCREEN_REGISTRY.filter((row) => row.access !== 'public');

beforeEach(() => {
  forgetEverySession();
  jar.value = null;
});

describe('the subject is the live registry, and every session row has a route file', () => {
  it('derives the session rows from the registry and finds a page for each', () => {
    // Not a hand list: the registry decides. W50 registers eighteen `session` rows.
    expect(SESSION_ROWS.length).toBeGreaterThanOrEqual(18);
    const pages = pageFiles();
    const missing = SESSION_ROWS.map((row) => row.address).filter((address) => !pages.has(address));
    expect(missing).toEqual([]);
  });
});

describe('decision 1: a guest is sent to /login with the concrete path and its query in next', () => {
  const QUERY = { view: 'table', page: '2' } as const;
  const QUERY_STRING = 'view=table&page=2';

  for (const row of SESSION_ROWS) {
    it(`${row.address}: no cookie → /login?next=<concrete path?query>`, async () => {
      const route = await routeAt(row.address);
      const { path, params } = filled(row.address);
      const expected = `${path}?${QUERY_STRING}`;
      const location = await sentTo(
        route({ params: Promise.resolve(params), searchParams: Promise.resolve({ ...QUERY }) }),
      );
      expect(location).toBe(`/login?next=${encodeURIComponent(expected)}`);
    });
  }

  for (const row of SESSION_ROWS) {
    it(`${row.address}: a cookie the register does not hold is a guest too`, async () => {
      jar.value = 'f'.repeat(64);
      const route = await routeAt(row.address);
      const { path, params } = filled(row.address);
      const location = await sentTo(route({ params: Promise.resolve(params), searchParams: Promise.resolve({}) }));
      expect(location).toBe(`/login?next=${encodeURIComponent(path)}`);
    });
  }

  it('a query with spaces, Cyrillic and a repeated key keeps every value in next', async () => {
    for (const row of SESSION_ROWS) {
      const route = await routeAt(row.address);
      const { path, params } = filled(row.address);
      const location = await sentTo(
        route({
          params: Promise.resolve(params),
          searchParams: Promise.resolve({ q: 'два слова', tag: ['a', 'b'] }),
        }),
      );
      expect(location, row.address).not.toBeNull();
      const next = new URL(location as string, 'http://qa.invalid').searchParams.get('next') ?? '';
      const [nextPath, nextQuery = ''] = next.split('?');
      expect(nextPath, row.address).toBe(path);
      expect([...new URLSearchParams(nextQuery)], row.address).toEqual([
        ['q', 'два слова'],
        ['tag', 'a'],
        ['tag', 'b'],
      ]);
    }
  });

  it('the screens open to a default credential still need a session: a guest is sent from them too', async () => {
    const extra = NON_PUBLIC_ROWS.filter((row) => row.access === 'open-to-default-credential');
    expect(extra.map((row) => row.address).sort()).toEqual(['/account', '/account/password']);
    for (const row of extra) {
      const route = await routeAt(row.address);
      const location = await sentTo(route({ params: Promise.resolve({}), searchParams: Promise.resolve({}) }));
      expect(location, row.address).toBe(`/login?next=${encodeURIComponent(row.address)}`);
    }
  });
});

describe('the way back: the next a guest carries is accepted where it is read', () => {
  it('for every session row, the guard’s next passes the validator unchanged and reaches the hidden field', async () => {
    for (const row of SESSION_ROWS) {
      const route = await routeAt(row.address);
      const { path, params } = filled(row.address);
      const location = await sentTo(
        route({ params: Promise.resolve(params), searchParams: Promise.resolve({ view: 'table' }) }),
      );
      const next = new URL(location as string, 'http://qa.invalid').searchParams.get('next');
      expect(next, row.address).toBe(`${path}?view=table`);
      // The BFF's after-sign-in redirect validates against the whole registry.
      expect(safeReturnPath(next), row.address).toBe(next);
      // The sign-in screen the guest lands on posts it back in its hidden field.
      const screen = await LoginRoute({ params: Promise.resolve({}), searchParams: Promise.resolve({ next: next as string }) });
      const markup = renderScreen(newClient(), screen);
      const field = new RegExp(`<input type="hidden" name="${SIGN_IN_NEXT_FIELD}" value="([^"]*)"`).exec(markup);
      expect(field?.[1]?.replace(/&amp;/g, '&'), row.address).toBe(next);
    }
  });
});
