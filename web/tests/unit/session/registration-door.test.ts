/**
 * `POST /bff/v1/registration`: an application, forwarded exactly as the exchange is.
 *
 * The same two boundaries the sign-in suite is about. **Towards the API** the password goes
 * once, in a JSON body, to `submitRegistration`, with the same credential handling as the
 * exchange and nothing else sent; **towards the browser** the answer is a `303` and nothing
 * more — no body, no cookie, no password. And the third thing this door owns: every refusal is
 * one of a closed six, carried in the address because a redirect has no body.
 *
 * The screens at `/register` and `/register/submitted` are `W51`'s. This suite asserts the
 * addresses and values the handler produces, which is the half of the agreement this task
 * owns; `W51`'s feature mirrors the six and holds its copy to this handler's.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { GET, POST } from '@/app/bff/v1/[...path]/route';
import { forgetEveryGuestBucket } from '@/app/bff/session/guest-throttle';
import { forgetEverySession, openSessionCount } from '@/app/bff/session/store';

import { conflict } from './account-fixture';

const UPSTREAM = 'http://api.test:8000';
const DEPLOYMENT_TOKEN = 'deployment-credential-a1b2';
const PASSWORD = 'пароль-заявителя-не-должен-утечь';

interface Seen {
  readonly path: string;
  readonly method: string;
  readonly authorization: string | null;
  readonly body: string;
}

let seen: Seen[] = [];
let answer: () => Response;

const ORIGINAL = {
  upstream: process.env.AUDITMANAGER_API_UPSTREAM,
  token: process.env.AUDITMANAGER_API_TOKEN,
};

const FORM = {
  login: '  applicant@example.test ',
  password: PASSWORD,
  confirm_password: PASSWORD,
  last_name: 'Заявкина',
  first_name: 'Мария',
  middle_name: 'Петровна',
};

function created(): Response {
  return new Response(JSON.stringify({ status: 'pending' }), {
    status: 201,
    headers: { 'content-type': 'application/json' },
  });
}

beforeEach(() => {
  forgetEverySession();
  forgetEveryGuestBucket();
  seen = [];
  answer = created;
  process.env.AUDITMANAGER_API_UPSTREAM = UPSTREAM;
  process.env.AUDITMANAGER_API_TOKEN = DEPLOYMENT_TOKEN;
  vi.stubGlobal('fetch', async (input: RequestInfo | URL, init?: RequestInit) => {
    const headers = new Headers(init?.headers ?? {});
    const raw = init?.body;
    seen.push({
      path: new URL(String(input)).pathname,
      method: init?.method ?? 'GET',
      authorization: headers.get('authorization'),
      body: raw === undefined || raw === null ? '' : new TextDecoder().decode(raw as ArrayBuffer),
    });
    return answer();
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

/** Post the application the way a browser posts a plain form. */
function apply(fields: Record<string, string> = FORM): Promise<Response> {
  return POST(
    new Request('http://web.test/bff/v1/registration', {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams(fields).toString(),
    }),
    { params: Promise.resolve({ path: ['registration'] }) },
  );
}

/** Sign in once, so the exchange's own credential handling can be compared with this door's. */
function signIn(): Promise<Response> {
  return POST(
    new Request('http://web.test/bff/v1/session', {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ login: 'кто-то', password: 'что-то' }).toString(),
    }),
    { params: Promise.resolve({ path: ['session'] }) },
  );
}

function refusalOf(response: Response): string | null {
  const location = response.headers.get('location');
  if (location === null) return null;
  const url = new URL(location, 'http://web.test');
  expect(url.pathname).toBe('/register');
  return url.searchParams.get('refusal');
}

describe('an application is forwarded once, and only a redirect comes back', () => {
  it('lands a recorded application on the submitted screen, with no body and no cookie', async () => {
    const response = await apply();
    expect(response.status).toBe(303);
    expect(response.headers.get('location')).toBe('/register/submitted');
    expect(response.headers.get('set-cookie')).toBeNull();
    const headers = [...response.headers.entries()].map(([k, v]) => `${k}: ${v}`).join('\n');
    const body = await response.text();
    expect(body).toBe('');
    expect(`${headers}\n${body}`).not.toContain(PASSWORD);
    expect(`${headers}\n${body}`).not.toContain(DEPLOYMENT_TOKEN);
    // An application opens no session.
    expect(openSessionCount()).toBe(0);
  });

  it('sends the contract’s body to submitRegistration, once, and nothing else', async () => {
    await apply();
    expect(seen.map((call) => `${call.method} ${call.path}`)).toEqual(['POST /registrations']);
    expect(JSON.parse((seen[0] as Seen).body)).toEqual({
      login: 'applicant@example.test',
      password: PASSWORD,
      last_name: 'Заявкина',
      first_name: 'Мария',
      middle_name: 'Петровна',
    });
    // The confirmation is checked here and never travels.
    expect((seen[0] as Seen).body).not.toContain('confirm');
  });

  it('presents exactly what the exchange presents, so it is forwarded as the exchange is', async () => {
    await signIn();
    await apply();
    const exchange = seen.find((call) => call.path === '/auth/token');
    const application = seen.find((call) => call.path === '/registrations');
    expect(exchange).toBeDefined();
    expect(application?.authorization).toBe(exchange?.authorization);
  });

  it('leaves out a patronymic left blank, rather than sending an empty one', async () => {
    await apply({ ...FORM, middle_name: '   ' });
    expect(JSON.parse((seen[0] as Seen).body)).not.toHaveProperty('middle_name');
    seen = [];
    const withoutField: Record<string, string> = { ...FORM };
    delete withoutField.middle_name;
    await apply(withoutField);
    expect(JSON.parse((seen[0] as Seen).body)).not.toHaveProperty('middle_name');
  });
});

describe('what this door refuses before anything is sent', () => {
  it('refuses a missing or blank required field, and a confirmation that is not the password', async () => {
    const incomplete: readonly Record<string, string>[] = [
      { ...FORM, login: '   ' },
      { ...FORM, password: '', confirm_password: '' },
      { ...FORM, last_name: ' ' },
      { ...FORM, first_name: '' },
      { ...FORM, confirm_password: `${PASSWORD}-опечатка` },
      // A password is bytes somebody typed: a trailing space is a different password.
      { ...FORM, confirm_password: `${PASSWORD} ` },
    ];
    // Eleven posts, one more than a guest's bucket holds: each case starts with a full one.
    for (const fields of incomplete) {
      forgetEveryGuestBucket();
      expect(refusalOf(await apply(fields)), JSON.stringify(fields)).toBe('validation');
    }
    for (const field of ['login', 'password', 'confirm_password', 'last_name', 'first_name']) {
      forgetEveryGuestBucket();
      const fields: Record<string, string> = { ...FORM };
      delete fields[field];
      expect(refusalOf(await apply(fields)), field).toBe('validation');
    }
    expect(seen).toEqual([]);
  });

  it('refuses a body that is not a form', async () => {
    const response = await POST(
      new Request('http://web.test/bff/v1/registration', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(FORM),
      }),
      { params: Promise.resolve({ path: ['registration'] }) },
    );
    expect(refusalOf(response)).toBe('validation');
    expect(seen).toEqual([]);
  });

  it('answers an unconfigured deployment as upstream and sends nothing', async () => {
    delete process.env.AUDITMANAGER_API_TOKEN;
    expect(refusalOf(await apply())).toBe('upstream');
    delete process.env.AUDITMANAGER_API_UPSTREAM;
    expect(refusalOf(await apply())).toBe('upstream');
    expect(seen).toEqual([]);
  });

  it('answers every other verb and every deeper address as no such door, forwarding nothing', async () => {
    const read = await GET(new Request('http://web.test/bff/v1/registration'), {
      params: Promise.resolve({ path: ['registration'] }),
    });
    expect(read.status).toBe(404);
    const deeper = await POST(
      new Request('http://web.test/bff/v1/registration/status', { method: 'POST' }),
      { params: Promise.resolve({ path: ['registration', 'status'] }) },
    );
    expect(deeper.status).toBe(404);
    expect(seen).toEqual([]);
  });
});

describe('the API’s answer becomes one of the closed six', () => {
  it('carries the three conflict reasons across by name', async () => {
    for (const reason of ['login_taken', 'request_pending', 'queue_full']) {
      answer = () => conflict(reason);
      expect(refusalOf(await apply())).toBe(reason);
    }
  });

  it('reads validation_failed as validation and a proxy’s 429 as throttled', async () => {
    answer = () => new Response('{}', { status: 422 });
    expect(refusalOf(await apply())).toBe('validation');
    answer = () => new Response('{}', { status: 429 });
    expect(refusalOf(await apply())).toBe('throttled');
  });

  it('answers everything it does not understand as upstream, never as a value it guessed', async () => {
    const unknown: readonly (() => Response)[] = [
      () => conflict('account_referenced'),
      () => conflict('last_admin'),
      () => conflict(42),
      () => new Response(JSON.stringify({ error_code: 'conflict' }), { status: 409 }),
      () => new Response('not json', { status: 409 }),
      () => new Response('{}', { status: 200 }),
      () => new Response('{}', { status: 401 }),
      () => new Response('{}', { status: 500 }),
      () => new Response('{}', { status: 503 }),
    ];
    for (const shape of unknown) {
      answer = shape;
      forgetEveryGuestBucket();
      expect(refusalOf(await apply())).toBe('upstream');
    }
  });

  it('never puts a reason, a message or the login in the address', async () => {
    answer = () => conflict('login_taken');
    const location = (await apply()).headers.get('location') as string;
    expect(location).toBe('/register?refusal=login_taken');
    expect(location).not.toContain('applicant');
  });
});
