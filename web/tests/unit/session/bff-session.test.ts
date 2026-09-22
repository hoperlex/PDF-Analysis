/**
 * The exchange, the logout and the credential the forwarder presents.
 *
 * This file drives the real route handler with real `Request` objects and a stubbed
 * upstream, because every claim worth making about sign-in is a claim about what crosses
 * one of two boundaries:
 *
 *   **towards the API** — the password is sent exactly once, to the exchange, and never
 *   with any other request;
 *   **towards the browser** — the minted token is not in the answer, in any header, in any
 *   cookie, or anywhere else a browser retains. What the browser gets is an opaque number.
 *
 * The stub is `globalThis.fetch`, which is what `forwardWithCredential` calls when the
 * route handler gives it no override. Recording every call is how "the password went out
 * once, to one address" is asserted rather than described.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { GET, POST } from '@/app/bff/v1/[...path]/route';
import {
  SESSION_CLOSE_PATH,
  SESSION_OPEN_PATH,
  SIGN_IN_LANDING_PATH,
  SIGN_IN_PATH,
  SIGN_IN_REFUSALS,
  signInRefusalUrl,
} from '@/features/sign-in';
import { BFF_BASE_PATH } from '@/shared/api/credentialed-forward';
import { SESSION_COOKIE, forgetEverySession, openSessionCount } from '@/app/bff/session/store';

const UPSTREAM = 'http://api.test:8000';
const DEPLOYMENT_TOKEN = 'deployment-credential-a1b2';
const MINTED = 'minted-token-for-the-reviewer-c3d4';
const LOGIN = 'проверяющий';
const PASSWORD = 'пароль-который-не-должен-утечь';

interface Seen {
  readonly url: string;
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

function mintedAnswer(expiresIn: number = 3600): Response {
  return new Response(JSON.stringify({ token: MINTED, expires_in: expiresIn }), {
    status: 200,
    headers: { 'content-type': 'application/json' },
  });
}

beforeEach(() => {
  forgetEverySession();
  seen = [];
  answer = () => mintedAnswer();
  process.env.AUDITMANAGER_API_UPSTREAM = UPSTREAM;
  process.env.AUDITMANAGER_API_TOKEN = DEPLOYMENT_TOKEN;
  vi.stubGlobal('fetch', async (input: RequestInfo | URL, init?: RequestInit) => {
    const headers = new Headers(init?.headers ?? {});
    const raw = init?.body;
    seen.push({
      url: String(input),
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
  if (ORIGINAL.upstream === undefined) delete process.env.AUDITMANAGER_API_UPSTREAM;
  else process.env.AUDITMANAGER_API_UPSTREAM = ORIGINAL.upstream;
  if (ORIGINAL.token === undefined) delete process.env.AUDITMANAGER_API_TOKEN;
  else process.env.AUDITMANAGER_API_TOKEN = ORIGINAL.token;
});

/** Post the sign-in form the way a browser posts it: form-encoded, no JavaScript. */
function signIn(fields: Record<string, string> = { login: LOGIN, password: PASSWORD }): Promise<Response> {
  const body = new URLSearchParams(fields);
  return POST(
    new Request(`http://web.test${SESSION_OPEN_PATH}`, {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    }),
    { params: Promise.resolve({ path: ['session'] }) },
  );
}

function signOut(cookie?: string): Promise<Response> {
  return POST(
    new Request(`http://web.test${SESSION_CLOSE_PATH}`, {
      method: 'POST',
      ...(cookie === undefined ? {} : { headers: { cookie } }),
    }),
    { params: Promise.resolve({ path: ['session', 'end'] }) },
  );
}

function listProjects(cookie?: string): Promise<Response> {
  return GET(
    new Request('http://web.test/bff/v1/projects', {
      ...(cookie === undefined ? {} : { headers: { cookie } }),
    }),
    { params: Promise.resolve({ path: ['projects'] }) },
  );
}

/** The `am_session=...` pair out of a `Set-Cookie`, ready to send back as `Cookie`. */
function cookieFrom(response: Response): string {
  const header = response.headers.get('set-cookie');
  expect(header).not.toBeNull();
  return (header as string).split(';')[0] as string;
}

describe('the exchange happens on the server, and the token stops there', () => {
  it('answers a redirect, not a body, and puts an opaque number in an HttpOnly cookie', async () => {
    const response = await signIn();
    expect(response.status).toBe(303);
    expect(response.headers.get('location')).toBe(SIGN_IN_LANDING_PATH);

    const cookie = response.headers.get('set-cookie') as string;
    expect(cookie).toContain('HttpOnly');
    expect(cookie).toContain('SameSite=Strict');
    expect(cookie.startsWith(`${SESSION_COOKIE}=`)).toBe(true);
    expect(openSessionCount()).toBe(1);
  });

  it('puts neither the token nor the password anywhere the browser can read', async () => {
    const response = await signIn();
    const headers = [...response.headers.entries()].map(([k, v]) => `${k}: ${v}`).join('\n');
    const body = await response.text();
    // Everything the browser receives, as one string: status line aside, this is all of it.
    const received = `${headers}\n${body}`;
    expect(received).not.toContain(MINTED);
    expect(received).not.toContain(PASSWORD);
    expect(received).not.toContain(DEPLOYMENT_TOKEN);
    expect(body).toBe('');
  });

  it('sends the password exactly once, to the exchange, and to nothing else', async () => {
    const opened = await signIn();
    const cookie = cookieFrom(opened);
    await listProjects(cookie);
    await listProjects(cookie);

    expect(seen).toHaveLength(3);
    const exchanges = seen.filter((call) => call.body.includes(PASSWORD));
    expect(exchanges).toHaveLength(1);
    expect(exchanges[0]?.url).toBe(`${UPSTREAM}/auth/token`);
    expect(exchanges[0]?.method).toBe('POST');
    expect(JSON.parse(exchanges[0]?.body as string)).toEqual({ login: LOGIN, password: PASSWORD });
  });

  it('presents the reviewer’s own credential once the session exists', async () => {
    const cookie = cookieFrom(await signIn());
    const response = await listProjects(cookie);
    expect(response.status).toBe(200);
    expect(seen.at(-1)?.authorization).toBe(`Bearer ${MINTED}`);
    expect(seen.at(-1)?.url).toBe(`${UPSTREAM}/projects`);
  });

  /**
   * This case asserted the opposite until the wave's own judge measured what it costs.
   *
   * `AUDITMANAGER_API_TOKEN` stopped being the shared bearer and became **the key the API
   * signs credentials with**. Presenting it upstream was useless — the API answers `401`
   * to it, driven and measured — and it put key material in an `Authorization` header on
   * every anonymous page view. So the premise was overturned, not the wording.
   *
   * Both halves are asserted: nothing leaves this tier, and the refusal is the contract's
   * own `401` rather than a locally invented shape.
   */
  it('sends nothing upstream when nobody has signed in', async () => {
    const response = await listProjects();
    expect(seen).toHaveLength(0);
    expect(response.status).toBe(401);
  });

  it('never puts the signing key in a header, signed in or not', async () => {
    await listProjects();
    expect(seen.map((call) => call.authorization)).not.toContain(`Bearer ${DEPLOYMENT_TOKEN}`);
  });
});

describe('the sign-in screen is told what happened without being told which half was wrong', () => {
  it('reports a rejected pair as one refusal, and opens no session', async () => {
    answer = () =>
      new Response(JSON.stringify({ error_code: 'authentication_required' }), { status: 401 });
    const response = await signIn();
    expect(response.status).toBe(303);
    expect(response.headers.get('location')).toBe(signInRefusalUrl('credentials'));
    expect(response.headers.get('set-cookie')).toBeNull();
    expect(openSessionCount()).toBe(0);
  });

  it('refuses an incomplete form without sending anything upstream', async () => {
    for (const fields of [{ login: LOGIN }, { password: PASSWORD }, { login: ' ', password: '' }]) {
      const response = await signIn(fields as Record<string, string>);
      expect(response.headers.get('location')).toBe(signInRefusalUrl('validation'));
    }
    expect(seen).toEqual([]);
    expect(openSessionCount()).toBe(0);
  });

  it('refuses when the deployment cannot reach the API, and sends nothing', async () => {
    delete process.env.AUDITMANAGER_API_TOKEN;
    expect((await signIn()).headers.get('location')).toBe(signInRefusalUrl('unconfigured'));
    delete process.env.AUDITMANAGER_API_UPSTREAM;
    expect((await signIn()).headers.get('location')).toBe(signInRefusalUrl('unconfigured'));
    expect(seen).toEqual([]);
  });

  it('refuses an answer it does not understand rather than inventing a session', async () => {
    const unusable: readonly (() => Response)[] = [
      () => new Response('{}', { status: 500 }),
      () => new Response('not json', { status: 200, headers: { 'content-type': 'application/json' } }),
      () => new Response(JSON.stringify({ expires_in: 3600 }), { status: 200 }),
      () => new Response(JSON.stringify({ token: MINTED }), { status: 200 }),
      () => mintedAnswer(0),
      () => mintedAnswer(99_999_999),
    ];
    for (const shape of unusable) {
      answer = shape;
      const response = await signIn();
      expect(response.headers.get('location')).toBe(signInRefusalUrl('upstream'));
      expect(response.headers.get('set-cookie')).toBeNull();
    }
    expect(openSessionCount()).toBe(0);
  });

  it('answers every refusal at an address that screen can render', () => {
    // The pin the handler's own copy of these three strings is held to. A rename on either
    // side is red here rather than a redirect to a screen that shows nothing.
    expect(SIGN_IN_PATH).toBe('/login');
    expect(SIGN_IN_LANDING_PATH).toBe('/projects');
    expect(SESSION_OPEN_PATH).toBe(`${BFF_BASE_PATH}/session`);
    expect(SESSION_CLOSE_PATH).toBe(`${BFF_BASE_PATH}/session/end`);
    for (const refusal of SIGN_IN_REFUSALS) {
      expect(signInRefusalUrl(refusal)).toBe(`${SIGN_IN_PATH}?refusal=${refusal}`);
    }
  });
});

describe('leaving ends the session on the server, not just in the browser', () => {
  it('forgets the credential, clears the cookie and sends the reviewer back to the screen', async () => {
    const cookie = cookieFrom(await signIn());
    expect(openSessionCount()).toBe(1);

    const response = await signOut(cookie);
    expect(response.status).toBe(303);
    expect(response.headers.get('location')).toBe(SIGN_IN_PATH);
    expect(response.headers.get('set-cookie')).toContain('Max-Age=0');
    expect(openSessionCount()).toBe(0);
  });

  it('leaves the old cookie opening nothing at all', async () => {
    const cookie = cookieFrom(await signIn());
    await signOut(cookie);
    seen = [];

    const response = await listProjects(cookie);
    expect(response.status).toBe(401);
    const envelope = (await response.json()) as { error_code: string };
    expect(envelope.error_code).toBe('authentication_required');
    // And nothing was forwarded with the deployment's credential in its place.
    expect(seen).toEqual([]);
    expect(response.headers.get('set-cookie')).toContain('Max-Age=0');
  });

  it('is harmless when there is no session to end', async () => {
    const response = await signOut();
    expect(response.status).toBe(303);
    expect(response.headers.get('location')).toBe(SIGN_IN_PATH);
  });
});

describe('the reserved segment is this tier’s own and never reaches the API', () => {
  it('answers a read of it here rather than forwarding the word `session` upstream', async () => {
    const response = await GET(new Request(`http://web.test${SESSION_OPEN_PATH}`), {
      params: Promise.resolve({ path: ['session'] }),
    });
    expect(response.status).toBe(404);
    expect(seen).toEqual([]);
  });

  it('answers an unknown door under it without forwarding either', async () => {
    const response = await POST(new Request('http://web.test/bff/v1/session/anything'), {
      params: Promise.resolve({ path: ['session', 'anything'] }),
    });
    expect(response.status).toBe(404);
    const envelope = (await response.json()) as { error_code: string };
    expect(envelope.error_code).toBe('not_found');
    expect(seen).toEqual([]);
  });
});
