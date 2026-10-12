/**
 * `W53-CLOSE` `C-15`, `C-16`, `C-17` and `C-19`: the four BFF findings of the 2026-10-12 review.
 *
 * Driven through the real route handler with real `Request` objects and a stubbed upstream
 * that answers by address, as `bff-session.test.ts` does, because each claim here is about
 * what crosses a boundary:
 *
 * - **C-15** — a form post another site makes a browser send is refused at each of the four
 *   doors *before* the guest bucket is charged or the body read, and the same post from this
 *   origin, or with no browser headers at all, still works;
 * - **C-16** — a sign-in over a live session deletes the old row, in memory and in the
 *   register file, instead of leaving it valid behind the overwritten cookie;
 * - **C-17** — the three operations the contract leaves open are sent with no `Authorization`
 *   header, and so never with `AUDITMANAGER_API_TOKEN`, the API's signing key;
 * - **C-19** — a successful `PATCH /users/{user_uid}` on the session's own account rewrites
 *   the subject exactly as `PATCH /me` does, and one on somebody else's leaves it alone.
 */

import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { PATCH, POST } from '@/app/bff/v1/[...path]/route';
import { forgetEveryGuestBucket } from '@/app/bff/session/guest-throttle';
import {
  credentialOf,
  dropTheInMemoryRegister,
  forgetEverySession,
  openSessionCount,
  subjectOf,
} from '@/app/bff/session/store';
import { initialsOf } from '@/app/bff/session/subject';
import { SESSION_STORE_VARIABLE } from '@/shared/config/session-store';

import { accountAnswer, accountBody, authenticationRequired } from './account-fixture';

const UPSTREAM = 'http://api.test:8000';
const DEPLOYMENT_TOKEN = 'deployment-signing-key-e5f6';
const OWN_UID = accountBody().user_uid as string;
const OTHER_UID = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4OTHER';
const PASSWORD = 'пароль-проверяющей';
const NEW_PASSWORD = 'новый-пароль-проверяющей';

interface Seen {
  readonly path: string;
  readonly method: string;
  readonly authorization: string | null;
}

let seen: Seen[] = [];
let minted = 0;
/** `getMe`. */
let me: () => Response;
/** `POST /auth/token`. */
let exchange: () => Response;
/** `PATCH /users/{user_uid}`. */
let users: () => Response;

const ORIGINAL = {
  upstream: process.env.AUDITMANAGER_API_UPSTREAM,
  token: process.env.AUDITMANAGER_API_TOKEN,
};

function mintedAnswer(): Response {
  minted += 1;
  return new Response(
    JSON.stringify({ token: `minted-${minted}`, expires_in: 3600, is_default_credential: false }),
    { status: 200, headers: { 'content-type': 'application/json' } },
  );
}

function respond(path: string, method: string): Response {
  if (method === 'POST' && path === '/auth/token') return exchange();
  if (method === 'POST' && path === '/auth/password') return mintedAnswer();
  if (method === 'GET' && path === '/me') return me();
  if (method === 'POST' && path === '/registrations/status') return authenticationRequired();
  if (method === 'POST' && path === '/registrations') {
    return new Response(JSON.stringify({ status: 'pending' }), { status: 201 });
  }
  if (method === 'PATCH' && path.startsWith('/users/')) return users();
  return new Response('[]', { status: 200, headers: { 'content-type': 'application/json' } });
}

beforeEach(() => {
  forgetEverySession();
  forgetEveryGuestBucket();
  seen = [];
  minted = 0;
  me = () => accountAnswer();
  exchange = mintedAnswer;
  users = () => accountAnswer();
  process.env.AUDITMANAGER_API_UPSTREAM = UPSTREAM;
  process.env.AUDITMANAGER_API_TOKEN = DEPLOYMENT_TOKEN;
  vi.stubGlobal('fetch', async (input: RequestInfo | URL, init?: RequestInit) => {
    const headers = new Headers(init?.headers ?? {});
    const method = init?.method ?? 'GET';
    const path = new URL(String(input)).pathname;
    seen.push({ path, method, authorization: headers.get('authorization') });
    return respond(path, method);
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  forgetEverySession();
  forgetEveryGuestBucket();
  if (ORIGINAL.upstream === undefined) delete process.env.AUDITMANAGER_API_UPSTREAM;
  else process.env.AUDITMANAGER_API_UPSTREAM = ORIGINAL.upstream;
  if (ORIGINAL.token === undefined) delete process.env.AUDITMANAGER_API_TOKEN;
  else process.env.AUDITMANAGER_API_TOKEN = ORIGINAL.token;
});

// ---------------------------------------------------------------------------------------
// The four doors, posted the way a browser posts a plain form
// ---------------------------------------------------------------------------------------

type Door = 'sign-in' | 'sign-out' | 'password' | 'registration';

const DOORS: Record<Door, { readonly path: string[]; readonly fields: Record<string, string> }> = {
  'sign-in': { path: ['session'], fields: { login: 'reviewer', password: PASSWORD } },
  'sign-out': { path: ['session', 'end'], fields: {} },
  password: {
    path: ['session', 'password'],
    fields: {
      current_password: PASSWORD,
      new_password: NEW_PASSWORD,
      confirm_new_password: NEW_PASSWORD,
    },
  },
  registration: {
    path: ['registration'],
    fields: {
      login: 'applicant@example.test',
      password: PASSWORD,
      confirm_password: PASSWORD,
      last_name: 'Заявкина',
      first_name: 'Мария',
    },
  },
};

/** What a browser adds to a post; `host` is what nginx forwards as `$http_host`. */
type BrowserHeaders = Record<string, string>;

const SAME_ORIGIN: BrowserHeaders = {
  host: 'stand.example:56441',
  origin: 'http://stand.example:56441',
  'sec-fetch-site': 'same-origin',
};

function post(door: Door, browser: BrowserHeaders = {}, cookie?: string): Promise<Response> {
  const { path, fields } = DOORS[door];
  return POST(
    new Request(`http://web.internal:3000/bff/v1/${path.join('/')}`, {
      method: 'POST',
      headers: {
        'content-type': 'application/x-www-form-urlencoded',
        ...browser,
        ...(cookie === undefined ? {} : { cookie }),
      },
      body: new URLSearchParams(fields).toString(),
    }),
    { params: Promise.resolve({ path }) },
  );
}

function cookieFrom(response: Response): string {
  const header = response.headers.get('set-cookie');
  expect(header, 'a session cookie').not.toBeNull();
  return (header as string).split(';')[0] as string;
}

function idFrom(cookie: string): string {
  return cookie.split('=')[1] as string;
}

async function signedIn(): Promise<string> {
  const response = await post('sign-in', SAME_ORIGIN);
  expect(response.headers.get('location')).toBe('/');
  return cookieFrom(response);
}

// ---------------------------------------------------------------------------------------
// C-15
// ---------------------------------------------------------------------------------------

/** Each a post another site made a browser send. */
const CROSS_SITE: Record<string, BrowserHeaders> = {
  'Sec-Fetch-Site: cross-site, no Origin': { host: 'stand.example:56441', 'sec-fetch-site': 'cross-site' },
  'an Origin naming another host': { host: 'stand.example:56441', origin: 'https://evil.example' },
  'an Origin on this host but another port': {
    host: 'stand.example:56441',
    origin: 'http://stand.example:8080',
  },
  'Origin: null, an opaque origin': { host: 'stand.example:56441', origin: 'null' },
  'a cross-site fetch metadata despite a matching Origin': {
    ...SAME_ORIGIN,
    'sec-fetch-site': 'cross-site',
  },
};

describe('C-15: the four form doors refuse a post another site made', () => {
  describe.each(Object.entries(CROSS_SITE))('%s', (_label, browser) => {
    it('sign-in: refused as validation, before the bucket or the form, and no session', async () => {
      // Twenty refusals: the bucket holds ten, so a door that charged it first would answer
      // `throttled` long before the end, and the same-origin sign-in after would be refused.
      for (let attempt = 0; attempt < 20; attempt += 1) {
        const response = await post('sign-in', browser);
        expect(response.status).toBe(303);
        expect(response.headers.get('location')).toBe('/login?refusal=validation');
        expect(response.headers.get('set-cookie')).toBeNull();
      }
      expect(seen).toEqual([]);
      expect(openSessionCount()).toBe(0);
      await signedIn();
    });

    it('registration: refused as validation, before the bucket or the form', async () => {
      for (let attempt = 0; attempt < 20; attempt += 1) {
        const response = await post('registration', browser);
        expect(response.status).toBe(303);
        expect(response.headers.get('location')).toBe('/register?refusal=validation');
      }
      expect(seen).toEqual([]);
      expect((await post('registration', SAME_ORIGIN)).headers.get('location')).toBe(
        '/register/submitted',
      );
    });

    it('sign-out: ends nothing, clears no cookie', async () => {
      const cookie = await signedIn();
      const response = await post('sign-out', browser, cookie);
      expect(response.status).toBe(303);
      expect(response.headers.get('location')).toBe('/');
      expect(response.headers.get('set-cookie')).toBeNull();
      expect(credentialOf(idFrom(cookie))).not.toBeNull();
    });

    it('password change: refused as validation, nothing sent, the session unchanged', async () => {
      const cookie = await signedIn();
      seen = [];
      const response = await post('password', browser, cookie);
      expect(response.status).toBe(303);
      expect(response.headers.get('location')).toBe('/account/password?outcome=validation');
      expect(response.headers.get('set-cookie')).toBeNull();
      expect(seen).toEqual([]);
      expect(credentialOf(idFrom(cookie))).toBe('minted-1');
    });
  });
});

describe('C-15: the same posts from this origin, or from no browser at all, still work', () => {
  /** Each a post the doors must accept. */
  const ACCEPTED: Record<string, BrowserHeaders> = {
    'same-origin, Origin and fetch metadata agree': SAME_ORIGIN,
    'no Origin and no fetch metadata (curl, an old browser)': {},
    'Sec-Fetch-Site: same-site with no Origin': { host: 'stand.example', 'sec-fetch-site': 'same-site' },
    'Sec-Fetch-Site: none (typed, or a bookmark)': { host: 'stand.example', 'sec-fetch-site': 'none' },
    'an https Origin on its default port against a Host without one': {
      host: 'stand.example',
      origin: 'https://stand.example',
      'sec-fetch-site': 'same-origin',
    },
    'an https Origin against a Host naming 443 explicitly': {
      host: 'stand.example:443',
      origin: 'https://stand.example',
    },
    'an https Origin behind an outer terminator that told nginx http': {
      host: 'stand.example',
      'x-forwarded-proto': 'http',
      origin: 'https://stand.example',
    },
    'no Host header: the request URL’s authority stands in': { origin: 'http://web.internal:3000' },
  };

  describe.each(Object.entries(ACCEPTED))('%s', (_label, browser) => {
    it('signs in, changes the password, signs out, and applies', async () => {
      const opened = await post('sign-in', browser);
      expect(opened.headers.get('location')).toBe('/');
      const cookie = cookieFrom(opened);

      const changed = await post('password', browser, cookie);
      expect(changed.headers.get('location')).toBe('/account/password?outcome=changed');
      const replacement = cookieFrom(changed);

      const closed = await post('sign-out', browser, replacement);
      expect(closed.headers.get('location')).toBe('/login');
      expect(closed.headers.get('set-cookie')).toContain('Max-Age=0');
      expect(openSessionCount()).toBe(0);

      expect((await post('registration', browser)).headers.get('location')).toBe('/register/submitted');
    });
  });
});

// ---------------------------------------------------------------------------------------
// C-16
// ---------------------------------------------------------------------------------------

describe('C-16: a sign-in over a live session closes the old one', () => {
  let directory: string;

  beforeEach(() => {
    directory = mkdtempSync(join(tmpdir(), 'w53c-edge-register-'));
    process.env[SESSION_STORE_VARIABLE] = join(directory, 'register.json');
    dropTheInMemoryRegister();
    forgetEverySession();
  });

  afterEach(() => {
    delete process.env[SESSION_STORE_VARIABLE];
    dropTheInMemoryRegister();
    rmSync(directory, { recursive: true, force: true });
  });

  it('deletes the row the request’s cookie names, here and in the register file', async () => {
    const first = await signedIn();
    expect(credentialOf(idFrom(first))).toBe('minted-1');

    const second = cookieFrom(await post('sign-in', SAME_ORIGIN, first));
    expect(idFrom(second)).not.toBe(idFrom(first));
    expect(credentialOf(idFrom(first))).toBeNull();
    expect(credentialOf(idFrom(second))).toBe('minted-2');
    expect(openSessionCount()).toBe(1);

    const file = readFileSync(process.env[SESSION_STORE_VARIABLE] as string, 'utf8');
    expect(file).not.toContain(idFrom(first));
    expect(file).not.toContain('minted-1');
    expect(file).toContain(idFrom(second));
    // And a process that has never seen either finds only the new one.
    dropTheInMemoryRegister();
    expect(credentialOf(idFrom(first))).toBeNull();
    expect(credentialOf(idFrom(second))).toBe('minted-2');
  });

  it('leaves the old session alone when the new sign-in is refused', async () => {
    const first = await signedIn();
    exchange = () => authenticationRequired();
    const refused = await post('sign-in', SAME_ORIGIN, first);
    expect(refused.headers.get('location')).toBe('/login?refusal=credentials');
    expect(credentialOf(idFrom(first))).toBe('minted-1');
  });
});

// ---------------------------------------------------------------------------------------
// C-17
// ---------------------------------------------------------------------------------------

describe('C-17: the operations the contract leaves open are sent no Authorization at all', () => {
  it('the exchange and getMe after it: none, then the minted credential', async () => {
    await signedIn();
    expect(seen.map((call) => `${call.method} ${call.path} ${String(call.authorization)}`)).toEqual([
      'POST /auth/token null',
      'GET /me Bearer minted-1',
    ]);
  });

  it('the registration status read after a refused exchange: none, on both calls', async () => {
    exchange = () => authenticationRequired();
    await post('sign-in', SAME_ORIGIN);
    expect(seen.map((call) => `${call.method} ${call.path} ${String(call.authorization)}`)).toEqual([
      'POST /auth/token null',
      'POST /registrations/status null',
    ]);
  });

  it('the application: none', async () => {
    await post('registration', SAME_ORIGIN);
    expect(seen.map((call) => `${call.method} ${call.path} ${String(call.authorization)}`)).toEqual([
      'POST /registrations null',
    ]);
  });

  it('never reads the signing key: both open doors work with it unset', async () => {
    delete process.env.AUDITMANAGER_API_TOKEN;
    await signedIn();
    expect((await post('registration', SAME_ORIGIN)).headers.get('location')).toBe(
      '/register/submitted',
    );
    process.env.AUDITMANAGER_API_TOKEN = DEPLOYMENT_TOKEN;
    exchange = () => authenticationRequired();
    await post('sign-in', SAME_ORIGIN);
    expect(seen.map((call) => call.authorization)).not.toContain(`Bearer ${DEPLOYMENT_TOKEN}`);
  });
});

// ---------------------------------------------------------------------------------------
// C-19
// ---------------------------------------------------------------------------------------

function updateUser(cookie: string, uid: string): Promise<Response> {
  return PATCH(
    new Request(`http://web.internal:3000/bff/v1/users/${uid}`, {
      method: 'PATCH',
      headers: { cookie, 'content-type': 'application/json' },
      body: JSON.stringify({ names: { last_name: 'Шмидт', first_name: 'Ändrea' } }),
    }),
    { params: Promise.resolve({ path: ['users', uid] }) },
  );
}

describe('C-19: a self-targeted updateUser refreshes the subject', () => {
  it('rewrites the row after PATCH /users/{own uid}, keeping the credential and the lifetime', async () => {
    me = () => accountAnswer({ roles: ['admin'] });
    const cookie = await signedIn();
    const before = subjectOf(idFrom(cookie));
    expect(before?.displayLabel).toBe('Проверяющая А. Б.');

    me = () => accountAnswer({ roles: ['admin'], display_label: 'Шмидт Ä.' });
    seen = [];
    const response = await updateUser(cookie, OWN_UID);
    expect(response.status).toBe(200);
    expect(response.headers.get('set-cookie')).toBeNull();
    expect(seen.map((call) => `${call.method} ${call.path}`)).toEqual([
      `PATCH /users/${OWN_UID}`,
      'GET /me',
    ]);
    const after = subjectOf(idFrom(cookie));
    expect(after).toMatchObject({ displayLabel: 'Шмидт Ä.', initials: 'ШÄ' });
    expect(credentialOf(idFrom(cookie))).toBe('minted-1');
    expect(after?.openedAt).toBe(before?.openedAt);
    expect(after?.expiresAt).toBe(before?.expiresAt);
  });

  it('leaves the row alone after editing somebody else', async () => {
    me = () => accountAnswer({ roles: ['admin'] });
    const cookie = await signedIn();
    me = () => accountAnswer({ roles: ['admin'] });
    const response = await updateUser(cookie, OTHER_UID);
    expect(response.status).toBe(200);
    expect(response.headers.get('set-cookie')).toBeNull();
    expect(subjectOf(idFrom(cookie))?.displayLabel).toBe('Проверяющая А. Б.');
    expect(openSessionCount()).toBe(1);
  });

  it('ends the session when the self-edit changed the roles and the credential died', async () => {
    me = () => accountAnswer({ roles: ['admin', 'expert'] });
    const cookie = await signedIn();
    me = () => authenticationRequired();
    const response = await updateUser(cookie, OWN_UID);
    expect(response.status).toBe(200);
    expect(response.headers.get('set-cookie')).toContain('Max-Age=0');
    expect(openSessionCount()).toBe(0);
  });

  it('signs in on a getMe without user_uid, and closes when the edit then cannot be placed', async () => {
    const withoutUid = accountBody({ roles: ['admin'] });
    delete withoutUid.user_uid;
    me = () => new Response(JSON.stringify(withoutUid), { status: 200 });
    const cookie = await signedIn();
    expect(openSessionCount()).toBe(1);
    const response = await updateUser(cookie, OWN_UID);
    expect(response.status).toBe(200);
    expect(response.headers.get('set-cookie')).toContain('Max-Age=0');
    expect(openSessionCount()).toBe(0);
  });

  it('reads nothing again when the edit was refused', async () => {
    const cookie = await signedIn();
    users = () => new Response('{}', { status: 422 });
    seen = [];
    const response = await updateUser(cookie, OWN_UID);
    expect(response.status).toBe(422);
    expect(seen.map((call) => `${call.method} ${call.path}`)).toEqual([`PATCH /users/${OWN_UID}`]);
    expect(openSessionCount()).toBe(1);
  });

  it('asks nothing of getMe for an address below an account', async () => {
    const cookie = await signedIn();
    seen = [];
    const response = await PATCH(
      new Request(`http://web.internal:3000/bff/v1/users/${OWN_UID}/archive`, {
        method: 'PATCH',
        headers: { cookie },
      }),
      { params: Promise.resolve({ path: ['users', OWN_UID, 'archive'] }) },
    );
    expect(response.status).toBe(200);
    expect(seen.map((call) => call.path)).toEqual([`/users/${OWN_UID}/archive`]);
  });
});

describe('C-19: initials stay one letter each', () => {
  it('does not expand a letter whose capital is two', () => {
    expect('ß'.toLocaleUpperCase('ru-RU')).toBe('SS');
    expect(initialsOf('ßmith Anna')).toBe('ßA');
    expect(initialsOf('Straße')).toBe('S');
    expect(initialsOf('ŉame ölga')).toBe('ŉÖ');
    expect(initialsOf('ß')).toBe('ß');
  });

  it('still capitalises every letter that has a one-letter capital', () => {
    expect(initialsOf('петрова а.')).toBe('ПА');
    expect(initialsOf('ǆemal ölga')).toBe('ǄÖ');
    expect(initialsOf('élodie')).toBe('É');
  });
});
