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
 *
 * Since `W49-BFF-01` one sign-in is up to two upstream calls on each branch — the exchange
 * and `getMe` when it succeeds, the exchange and the registration status read when it is
 * refused — so the stub answers by **address**: `answer` is the exchange, `me` is `getMe`,
 * `status` is `readRegistrationStatus` and `other` is everything the catch-all forwards.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { GET, PATCH, POST } from '@/app/bff/v1/[...path]/route';
import {
  SESSION_CLOSE_PATH,
  SESSION_OPEN_PATH,
  SIGN_IN_LANDING_PATH,
  SIGN_IN_PATH,
  SIGN_IN_REFUSALS,
  signInRefusalUrl,
} from '@/features/sign-in';
import { BFF_BASE_PATH } from '@/shared/api/credentialed-forward';
import { forgetEveryGuestBucket } from '@/app/bff/session/guest-throttle';
import {
  SESSION_COOKIE,
  credentialOf,
  forgetEverySession,
  openSessionCount,
  subjectOf,
} from '@/app/bff/session/store';

import {
  ACCOUNT_LABEL,
  ACCOUNT_LOGIN,
  accountAnswer,
  authenticationRequired,
} from './account-fixture';

const UPSTREAM = 'http://api.test:8000';
const DEPLOYMENT_TOKEN = 'deployment-credential-a1b2';
const MINTED = 'minted-token-for-the-reviewer-c3d4';
const LOGIN = 'проверяющий';
const PASSWORD = 'пароль-который-не-должен-утечь';

interface Seen {
  readonly url: string;
  readonly path: string;
  readonly method: string;
  readonly authorization: string | null;
  readonly body: string;
}

let seen: Seen[] = [];
/** The exchange, `POST /auth/token`. */
let answer: () => Response;
/** `getMe`, `GET /me`. */
let me: () => Response;
/** `readRegistrationStatus`, `POST /registrations/status`. */
let status: () => Response;
/** Everything else the catch-all forwards. */
let other: () => Response;

const ORIGINAL = {
  upstream: process.env.AUDITMANAGER_API_UPSTREAM,
  token: process.env.AUDITMANAGER_API_TOKEN,
};

function respond(path: string, method: string): Response {
  if (method === 'POST' && path === '/auth/token') return answer();
  if (method === 'GET' && path === '/me') return me();
  if (method === 'POST' && path === '/registrations/status') return status();
  return other();
}

/**
 * What the API answers a successful exchange with, as the contract declares it.
 *
 * All three properties, because all three are required on `IssueTokenResponse` since
 * `R-50`, and the handler refuses a body missing any of them rather than defaulting it.
 * `isDefault` is a parameter and not a constant so the two states are both drivable here:
 * a fixture that could only produce one of them would leave the other to the journey.
 */
function mintedAnswer(expiresIn: number = 3600, isDefault = false): Response {
  return new Response(
    JSON.stringify({ token: MINTED, expires_in: expiresIn, is_default_credential: isDefault }),
    {
      status: 200,
      headers: { 'content-type': 'application/json' },
    },
  );
}

beforeEach(() => {
  forgetEverySession();
  forgetEveryGuestBucket();
  seen = [];
  answer = () => mintedAnswer();
  me = () => accountAnswer();
  status = () => authenticationRequired();
  other = () => new Response('[]', { status: 200, headers: { 'content-type': 'application/json' } });
  process.env.AUDITMANAGER_API_UPSTREAM = UPSTREAM;
  process.env.AUDITMANAGER_API_TOKEN = DEPLOYMENT_TOKEN;
  vi.stubGlobal('fetch', async (input: RequestInfo | URL, init?: RequestInit) => {
    const headers = new Headers(init?.headers ?? {});
    const raw = init?.body;
    const method = init?.method ?? 'GET';
    const path = new URL(String(input)).pathname;
    seen.push({
      url: String(input),
      path,
      method,
      authorization: headers.get('authorization'),
      body: raw === undefined || raw === null ? '' : new TextDecoder().decode(raw as ArrayBuffer),
    });
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

describe('R-50: where a sign-in lands, and what the register was told', () => {
  it('lands a changed password on the application and a seeded one on the change screen', async () => {
    answer = () => mintedAnswer(3600, false);
    expect((await signIn()).headers.get('location')).toBe(SIGN_IN_LANDING_PATH);

    forgetEverySession();
    answer = () => mintedAnswer(3600, true);
    const forced = await signIn();
    // Both assertions, because "not the project list" would pass on a redirect to
    // anywhere -- including back to the sign-in screen, which is what a refusal looks like.
    expect(forced.headers.get('location')).toBe('/account/password');
    expect(forced.status).toBe(303);
    // And it IS a session: the reviewer is signed in and sent somewhere, not turned away.
    expect(openSessionCount()).toBe(1);
  });

  it('records what the API said and never what this tier assumed', async () => {
    answer = () => mintedAnswer(3600, true);
    const cookie = cookieFrom(await signIn());
    const id = cookie.split('=')[1] as string;
    expect(subjectOf(id)?.isDefaultCredential).toBe(true);

    forgetEverySession();
    answer = () => mintedAnswer(3600, false);
    const second = cookieFrom(await signIn());
    expect(subjectOf(second.split('=')[1] as string)?.isDefaultCredential).toBe(false);
  });

  it('takes the stricter of the exchange and getMe, which report the same column', async () => {
    // A moment apart, the two answers can disagree only if the column changed between
    // them. Either saying the password must change is enough: that is the API's answer,
    // the restrictive one, and not a value this tier made up.
    answer = () => mintedAnswer(3600, false);
    me = () => accountAnswer({ is_default_credential: true });
    const response = await signIn();
    expect(response.headers.get('location')).toBe('/account/password');
    expect(subjectOf(cookieFrom(response).split('=')[1] as string)?.isDefaultCredential).toBe(true);
  });
});

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

    // The exchange, `getMe`, and the two reads.
    expect(seen).toHaveLength(4);
    const exchanges = seen.filter((call) => call.body.includes(PASSWORD));
    expect(exchanges).toHaveLength(1);
    expect(exchanges[0]?.url).toBe(`${UPSTREAM}/auth/token`);
    expect(exchanges[0]?.method).toBe('POST');
    expect(JSON.parse(exchanges[0]?.body as string)).toEqual({ login: LOGIN, password: PASSWORD });
    // A successful exchange is never followed by the registration status read.
    expect(seen.map((call) => call.path)).not.toContain('/registrations/status');
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
    // And `getMe` was never asked: there is no credential to ask it with.
    expect(seen.map((call) => call.path)).not.toContain('/me');
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
      // `R-50`. A body carrying the two older properties and not the required third is an
      // answer this tier does not understand. It is refused rather than read as `false`,
      // which is the value that would let a reviewer on the seeded password walk past the
      // screen the ruling sends them to.
      () =>
        new Response(JSON.stringify({ token: MINTED, expires_in: 3600 }), { status: 200 }),
      () =>
        new Response(
          JSON.stringify({ token: MINTED, expires_in: 3600, is_default_credential: 'yes' }),
          { status: 200 },
        ),
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

/** The session id a sign-in's cookie carries. */
function idFrom(cookie: string): string {
  return cookie.split('=')[1] as string;
}

/** `PATCH /me` through the catch-all, as the generated client sends it. */
function updateMyProfile(cookie: string, body: Record<string, unknown>): Promise<Response> {
  return PATCH(
    new Request('http://web.test/bff/v1/me', {
      method: 'PATCH',
      headers: { cookie, 'content-type': 'application/json' },
      body: JSON.stringify(body),
    }),
    { params: Promise.resolve({ path: ['me'] }) },
  );
}

describe('W49: the session holds the subject getMe describes, never one this tier guessed', () => {
  it('opens the row with getMe’s six fields, read with the minted credential', async () => {
    me = () =>
      accountAnswer({ roles: ['admin', 'expert'], is_default_credential: false, profile_complete: true });
    const cookie = cookieFrom(await signIn());

    const call = seen.find((entry) => entry.path === '/me');
    expect(call?.method).toBe('GET');
    expect(call?.authorization).toBe(`Bearer ${MINTED}`);
    expect(call?.body).toBe('');

    const subject = subjectOf(idFrom(cookie));
    expect(subject).toMatchObject({
      // The account's login from the API, not the one typed into the form.
      login: ACCOUNT_LOGIN,
      displayLabel: ACCOUNT_LABEL,
      initials: 'ПА',
      roles: ['admin', 'expert'],
      isDefaultCredential: false,
      profileComplete: true,
    });
    expect(subject?.login).not.toBe(LOGIN);
    expect(Object.keys(subject as object).sort()).toEqual([
      'displayLabel',
      'expiresAt',
      'initials',
      'isDefaultCredential',
      'login',
      'openedAt',
      'profileComplete',
      'roles',
    ]);
    expect(JSON.stringify(subject)).not.toContain(MINTED);
  });

  it('records an incomplete legacy profile as incomplete, with no roles invented', async () => {
    me = () =>
      accountAnswer({
        login: 'admin',
        display_label: 'admin',
        last_name: null,
        first_name: null,
        middle_name: null,
        roles: [],
        profile_complete: false,
      });
    const subject = subjectOf(idFrom(cookieFrom(await signIn())));
    expect(subject?.profileComplete).toBe(false);
    expect(subject?.roles).toEqual([]);
    expect(subject?.initials).toBe('A');
  });

  it('opens no session when getMe does not describe a subject it understands', async () => {
    const unusable: readonly (() => Response)[] = [
      () => authenticationRequired(),
      () => new Response('{}', { status: 500 }),
      () => new Response('not json', { status: 200 }),
      () => accountAnswer({ roles: ['expert', 'owner'] }),
      () => accountAnswer({ roles: ['expert', 'expert'] }),
      () => accountAnswer({ roles: 'expert' }),
      () => accountAnswer({ profile_complete: undefined }),
      () => accountAnswer({ is_default_credential: 'no' }),
      () => accountAnswer({ display_label: '' }),
      () => accountAnswer({ login: 42 }),
    ];
    for (const shape of unusable) {
      forgetEveryGuestBucket();
      me = shape;
      const response = await signIn();
      expect(response.headers.get('location')).toBe(signInRefusalUrl('upstream'));
      expect(response.headers.get('set-cookie')).toBeNull();
    }
    expect(openSessionCount()).toBe(0);
  });
});

describe('R-56 addendum: sign-in shows a pending application and nothing else', () => {
  beforeEach(() => {
    answer = () => authenticationRequired();
  });

  it('sends a pair that proves a pending application to the pending refusal', async () => {
    status = () =>
      new Response(JSON.stringify({ status: 'pending' }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      });
    const response = await signIn();
    expect(response.status).toBe(303);
    expect(response.headers.get('location')).toBe(signInRefusalUrl('pending'));
    expect(response.headers.get('set-cookie')).toBeNull();
    expect(openSessionCount()).toBe(0);
  });

  it('asks the status read with the same pair, and sends the password nowhere else', async () => {
    await signIn();
    expect(seen.map((call) => `${call.method} ${call.path}`)).toEqual([
      'POST /auth/token',
      'POST /registrations/status',
    ]);
    const statusCall = seen[1] as Seen;
    expect(JSON.parse(statusCall.body)).toEqual({ login: LOGIN, password: PASSWORD });
    // The same credential handling as the exchange it follows.
    expect(statusCall.authorization).toBe((seen[0] as Seen).authorization);
    expect(seen.filter((call) => call.body.includes(PASSWORD))).toHaveLength(2);
  });

  it('answers a rejected or unknown pair with the generic refusal, never with pending', async () => {
    // The status read answers every pair but a pending one with the exchange's own 401 --
    // an unknown login, a wrong password, and a decided request alike.
    status = () => authenticationRequired();
    const response = await signIn();
    expect(response.headers.get('location')).toBe(signInRefusalUrl('credentials'));
    expect(response.headers.get('location')).not.toBe(signInRefusalUrl('pending'));
  });

  it('reads only a 200 naming pending as pending; every other answer is the generic refusal', async () => {
    const notPending: readonly (() => Response)[] = [
      () => new Response(JSON.stringify({ status: 'rejected' }), { status: 200 }),
      () => new Response(JSON.stringify({ status: 'approved' }), { status: 200 }),
      () => new Response(JSON.stringify({}), { status: 200 }),
      () => new Response('null', { status: 200 }),
      () => new Response('not json', { status: 200 }),
      () => new Response(JSON.stringify({ status: 'pending' }), { status: 201 }),
      () => new Response(JSON.stringify({ status: 'pending' }), { status: 422 }),
      () => new Response('{}', { status: 500 }),
      () => new Response('{}', { status: 503 }),
    ];
    for (const shape of notPending) {
      forgetEveryGuestBucket();
      status = shape;
      const response = await signIn();
      expect(response.headers.get('location')).toBe(signInRefusalUrl('credentials'));
    }
  });

  it('reads a proxy’s 429 on the exchange as the per-client throttled refusal', async () => {
    answer = () => new Response('{}', { status: 429 });
    const response = await signIn();
    expect(response.headers.get('location')).toBe(signInRefusalUrl('throttled'));
    expect(seen.map((call) => call.path)).toEqual(['/auth/token']);
  });
});

describe('an upstream 401 on a held credential closes the session and answers the envelope', () => {
  it('deletes the row, clears the cookie and returns the API’s own 401 envelope', async () => {
    const cookie = cookieFrom(await signIn());
    expect(openSessionCount()).toBe(1);

    other = () => authenticationRequired('api-epoch-raised');
    const response = await listProjects(cookie);

    // The envelope, not a redirect: the caller is the generated client's fetch.
    expect(response.status).toBe(401);
    expect(response.headers.get('location')).toBeNull();
    const envelope = (await response.json()) as { error_code: string; correlation_id: string };
    expect(envelope.error_code).toBe('authentication_required');
    expect(envelope.correlation_id).toBe('api-epoch-raised');
    expect(response.headers.get('set-cookie'), 'the cookie is cleared in the same answer').not.toBeNull();
    expect(response.headers.get('set-cookie')).toContain('Max-Age=0');
    expect(response.headers.get('set-cookie')).toContain(`${SESSION_COOKIE}=;`);

    // The row is gone, here as well as there.
    expect(openSessionCount()).toBe(0);
    expect(subjectOf(idFrom(cookie))).toBeNull();
    expect(credentialOf(idFrom(cookie))).toBeNull();

    // And the browser's old cookie now opens nothing: no further request goes out with it.
    seen = [];
    const after = await listProjects(cookie);
    expect(after.status).toBe(401);
    expect(seen).toEqual([]);
  });

  it('keeps the session on every other refusal, which is about the request and not the credential', async () => {
    const cookie = cookieFrom(await signIn());
    for (const statusCode of [403, 404, 409, 422, 500, 503]) {
      other = () => new Response('{}', { status: statusCode });
      const response = await listProjects(cookie);
      expect(response.status).toBe(statusCode);
      expect(response.headers.get('set-cookie')).toBeNull();
    }
    expect(openSessionCount()).toBe(1);
    expect(credentialOf(idFrom(cookie))).toBe(MINTED);
  });
});

describe('W49: a successful profile change rewrites the subject without a new sign-in', () => {
  it('re-reads getMe after PATCH /me and rewrites the row in place', async () => {
    me = () =>
      accountAnswer({
        login: 'admin',
        display_label: 'admin',
        last_name: null,
        first_name: null,
        middle_name: null,
        profile_complete: false,
      });
    const cookie = cookieFrom(await signIn());
    const before = subjectOf(idFrom(cookie));
    expect(before?.profileComplete).toBe(false);

    other = () => accountAnswer();
    me = () => accountAnswer();
    seen = [];
    const response = await updateMyProfile(cookie, {
      email: ACCOUNT_LOGIN,
      last_name: 'Проверяющая',
      first_name: 'Анна',
    });
    expect(response.status).toBe(200);
    expect(response.headers.get('set-cookie')).toBeNull();
    expect(seen.map((call) => `${call.method} ${call.path}`)).toEqual(['PATCH /me', 'GET /me']);
    expect(seen[1]?.authorization).toBe(`Bearer ${MINTED}`);

    const after = subjectOf(idFrom(cookie));
    expect(after).toMatchObject({
      login: ACCOUNT_LOGIN,
      displayLabel: ACCOUNT_LABEL,
      initials: 'ПА',
      profileComplete: true,
    });
    // The same session: the same credential and the lifetime the exchange granted.
    expect(credentialOf(idFrom(cookie))).toBe(MINTED);
    expect(after?.openedAt).toBe(before?.openedAt);
    expect(after?.expiresAt).toBe(before?.expiresAt);
    expect(openSessionCount()).toBe(1);
  });

  it('reads nothing again when the change was refused', async () => {
    const cookie = cookieFrom(await signIn());
    other = () => new Response('{}', { status: 422 });
    seen = [];
    const response = await updateMyProfile(cookie, { last_name: '', first_name: '' });
    expect(response.status).toBe(422);
    expect(seen.map((call) => call.path)).toEqual(['/me']);
    expect(seen[0]?.method).toBe('PATCH');
  });

  it('ends the session when the refresh cannot say who it belongs to now', async () => {
    const cookie = cookieFrom(await signIn());
    other = () => accountAnswer();
    me = () => new Response('{}', { status: 503 });
    const response = await updateMyProfile(cookie, { last_name: 'Проверяющая', first_name: 'Анна' });
    // The change itself was made and is reported as made; the session is closed so the next
    // sign-in reads the subject again, rather than this tier keeping one it knows is stale.
    expect(response.status).toBe(200);
    expect(response.headers.get('set-cookie'), 'the cookie is cleared in the same answer').not.toBeNull();
    expect(response.headers.get('set-cookie')).toContain('Max-Age=0');
    expect(openSessionCount()).toBe(0);
  });

  it('does not refresh on a read of /me, which changes nothing', async () => {
    const cookie = cookieFrom(await signIn());
    other = () => accountAnswer();
    seen = [];
    await GET(new Request('http://web.test/bff/v1/me', { headers: { cookie } }), {
      params: Promise.resolve({ path: ['me'] }),
    });
    expect(seen).toHaveLength(1);
  });
});

describe('the registrations segment is refused to the browser, with or without a session', () => {
  const ADDRESSES: readonly (readonly string[])[] = [
    ['registrations'],
    ['registrations', 'status'],
    ['registrations', 'reg_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', 'approve'],
    ['registrations', 'reg_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', 'reject'],
  ];

  async function ask(
    method: typeof GET,
    verb: string,
    path: readonly string[],
    cookie?: string,
  ): Promise<Response> {
    return method(
      new Request(`http://web.test/bff/v1/${path.join('/')}`, {
        method: verb,
        headers: {
          'content-type': 'application/json',
          ...(cookie === undefined ? {} : { cookie }),
        },
        ...(verb === 'POST' ? { body: JSON.stringify({ login: LOGIN, password: PASSWORD }) } : {}),
      }),
      { params: Promise.resolve({ path: [...path] }) },
    );
  }

  it('answers not_found and forwards nothing without a session', async () => {
    for (const path of ADDRESSES) {
      for (const [method, verb] of [
        [GET, 'GET'],
        [POST, 'POST'],
      ] as const) {
        const response = await ask(method, verb, path);
        expect(response.status, `${verb} ${path.join('/')}`).toBe(404);
        expect(((await response.json()) as { error_code: string }).error_code).toBe('not_found');
      }
    }
    expect(seen).toEqual([]);
  });

  it('answers not_found and forwards nothing with a live session either', async () => {
    const cookie = cookieFrom(await signIn());
    seen = [];
    for (const path of ADDRESSES) {
      for (const [method, verb] of [
        [GET, 'GET'],
        [POST, 'POST'],
      ] as const) {
        const response = await ask(method, verb, path, cookie);
        expect(response.status, `${verb} ${path.join('/')}`).toBe(404);
        // Refused before the session is read: the session is untouched, not cleared.
        expect(response.headers.get('set-cookie')).toBeNull();
      }
    }
    // Not one request went out under the reviewer's credential.
    expect(seen).toEqual([]);
    expect(openSessionCount()).toBe(1);
  });

  it('still forwards a segment that merely starts with the same letters', async () => {
    // The control: the refusal is of the segment, not of a prefix. A path the contract
    // does not have is the API's to refuse, and it is forwarded like any other.
    const cookie = cookieFrom(await signIn());
    seen = [];
    await GET(new Request('http://web.test/bff/v1/registrationsx', { headers: { cookie } }), {
      params: Promise.resolve({ path: ['registrationsx'] }),
    });
    expect(seen.map((call) => call.path)).toEqual(['/registrationsx']);
  });
});
