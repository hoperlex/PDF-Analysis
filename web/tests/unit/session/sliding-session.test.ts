/**
 * The sliding session (owner ruling of 2026-11-18): a reviewer who is working is not signed out.
 *
 * The real route handler, real `Request` objects, the real register -- and an API that is a
 * stub **with a clock of its own**: it knows which credentials it minted and when each one
 * expires, and refuses an unknown or expired one with the contract's `401`. A session that
 * stays alive here therefore stays alive because the web tier renewed its credential, and not
 * because the stub is lenient. Time is the system clock, set by `vi.setSystemTime` (only `Date`
 * is faked), which is what the route handler and the register read.
 *
 * The numbers are the owner's: an 8 hour idle limit (the API's credential lives 8 h 10 min, the
 * idle window plus the 10 minute renewal cadence), a 30 day absolute cap from sign-in, renewal
 * on the first request that finds the credential more than 600 s old. Every guard has a test
 * that goes red when the guard is removed; the mutations are in the hand-over.
 */

import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { GET, POST } from '@/app/bff/v1/[...path]/route';
import { guestSessionReasonFromHeader } from '@/app/bff/session/end-note';
import { forgetEveryGuestBucket } from '@/app/bff/session/guest-throttle';
import { forgetEveryRenewalInFlight } from '@/app/bff/session/renewal';
import {
  RENEW_AFTER_SECONDS,
  SESSION_ABSOLUTE_CAP_SECONDS,
  credentialOf,
  dropTheInMemoryRegister,
  forgetEverySession,
  openSession,
  openSessionCount,
  remainingCapSeconds,
  renewalDue,
  sessionLapsed,
  subjectOf,
} from '@/app/bff/session/store';
import type { SessionAccount } from '@/app/bff/session/store';

import { accountAnswer } from './account-fixture';

const UPSTREAM = 'http://api.renew1118:8000';
const DEPLOYMENT_TOKEN = 'deployment-credential-renew1118';

const SECOND = 1000;
const MINUTE = 60 * SECOND;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/** What the API mints: the idle window and the renewal cadence (`TOKEN_LIFETIME_SECONDS`). */
const API_LIFETIME_SECONDS = 8 * 3600 + 600;
const API_LIFETIME_MS = API_LIFETIME_SECONDS * SECOND;

const T0 = Date.UTC(2026, 10, 18, 9, 0, 0);

const ACCOUNT: SessionAccount = {
  userUid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
  login: 'reviewer@example.test',
  displayLabel: 'Проверяющая А. Б.',
  initials: 'ПА',
  roles: ['expert'],
  isDefaultCredential: false,
  profileComplete: true,
};

type RenewMode = 'ok' | 'unauthorized' | 'unavailable' | 'unreachable';

/** The API's side: every credential it minted, with the instant it stops being accepted. */
let accepted: Map<string, number>;
let minted: number;
/** Every `renewToken` call, with the credential it was presented. */
let renewCalls: string[];
/** Every other forwarded call (not the exchange, not `getMe`, not the renewal). */
let forwarded: { readonly path: string; readonly authorization: string | null }[];
let renewMode: RenewMode;
/** When set, a renewal does not answer until this resolves: how concurrency is made to overlap. */
let renewGate: Promise<void> | null;
let warnings: string[];
let storeDirectory: string | null;

const ORIGINAL = {
  upstream: process.env.AUDITMANAGER_API_UPSTREAM,
  token: process.env.AUDITMANAGER_API_TOKEN,
  store: process.env.AUDITMANAGER_SESSION_STORE,
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

function envelope(correlationId: string, status = 401): Response {
  return new Response(
    JSON.stringify({
      contract_version: '1.59.0',
      correlation_id: correlationId,
      error_code: status === 401 ? 'authentication_required' : 'dependency_unavailable',
      message: 'The credential is not accepted.',
      retryable: false,
    }),
    {
      status,
      headers: { 'content-type': 'application/json', 'x-correlation-id': correlationId },
    },
  );
}

/** Mint a credential on the API's side, as of the system clock. */
function mint(): Response {
  minted += 1;
  const token = `cred-${String(minted)}`;
  accepted.set(token, Date.now() + API_LIFETIME_MS);
  return json({ token, expires_in: API_LIFETIME_SECONDS, is_default_credential: false });
}

function accepts(authorization: string | null): boolean {
  if (authorization === null) return false;
  const expiry = accepted.get(authorization.replace(/^Bearer /, ''));
  return expiry !== undefined && expiry > Date.now();
}

async function respond(path: string, method: string, authorization: string | null): Promise<Response> {
  if (method === 'POST' && path === '/auth/token') return mint();
  if (method === 'POST' && path === '/auth/token/renew') {
    renewCalls.push(authorization ?? '(none)');
    if (renewGate !== null) await renewGate;
    if (renewMode === 'unreachable') throw new TypeError('fetch failed');
    if (renewMode === 'unavailable') return envelope('api-renew-503', 503);
    if (renewMode === 'unauthorized' || !accepts(authorization)) return envelope('api-renew-401');
    return mint();
  }
  if (method === 'GET' && path === '/me') {
    return accepts(authorization) ? accountAnswer() : envelope('api-me-401');
  }
  forwarded.push({ path, authorization });
  return accepts(authorization) ? json([]) : envelope('api-forward-401');
}

/** Set the clock to `offset` after the sign-in instant. */
function at(offset: number): void {
  vi.setSystemTime(T0 + offset);
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(T0);
  forgetEverySession();
  forgetEveryRenewalInFlight();
  forgetEveryGuestBucket();
  accepted = new Map();
  minted = 0;
  renewCalls = [];
  forwarded = [];
  renewMode = 'ok';
  renewGate = null;
  warnings = [];
  storeDirectory = null;
  process.env.AUDITMANAGER_API_UPSTREAM = UPSTREAM;
  process.env.AUDITMANAGER_API_TOKEN = DEPLOYMENT_TOKEN;
  delete process.env.AUDITMANAGER_SESSION_STORE;
  vi.spyOn(console, 'warn').mockImplementation((line: unknown) => {
    if (typeof line === 'string' && line.startsWith('[session-renew]')) warnings.push(line);
  });
  vi.stubGlobal('fetch', async (input: RequestInfo | URL, init?: RequestInit) => {
    const headers = new Headers(init?.headers ?? {});
    return respond(new URL(String(input)).pathname, init?.method ?? 'GET', headers.get('authorization'));
  });
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  forgetEverySession();
  forgetEveryRenewalInFlight();
  forgetEveryGuestBucket();
  if (storeDirectory !== null) rmSync(storeDirectory, { recursive: true, force: true });
  for (const [name, value] of [
    ['AUDITMANAGER_API_UPSTREAM', ORIGINAL.upstream],
    ['AUDITMANAGER_API_TOKEN', ORIGINAL.token],
    ['AUDITMANAGER_SESSION_STORE', ORIGINAL.store],
  ] as const) {
    if (value === undefined) delete process.env[name];
    else process.env[name] = value;
  }
});

/** Sign in through the real door and return what the browser keeps: both cookies. */
async function signIn(): Promise<{ readonly cookie: string; readonly id: string; readonly lines: string[] }> {
  const response = await POST(
    new Request('http://web.test/bff/v1/session', {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ login: 'reviewer@example.test', password: 'a-password' }).toString(),
    }),
    { params: Promise.resolve({ path: ['session'] }) },
  );
  expect(response.status).toBe(303);
  const lines = response.headers.getSetCookie();
  const pair = lines.find((line) => line.startsWith('am_session='))?.split(';')[0];
  expect(pair).toBeDefined();
  return { cookie: pair as string, id: (pair as string).split('=')[1] as string, lines };
}

function listProjects(cookie: string): Promise<Response> {
  return GET(new Request('http://web.test/bff/v1/projects', { headers: { cookie } }), {
    params: Promise.resolve({ path: ['projects'] }),
  });
}

describe('a request keeps the session alive by renewing its credential', () => {
  it('a request every 50 minutes keeps a session alive over 5 hours, and renews each time', async () => {
    const { cookie, id } = await signIn();
    const opened = subjectOf(id)?.openedAt;
    expect(credentialOf(id)).toBe('cred-1');

    for (let minute = 50; minute <= 300; minute += 50) {
      at(minute * MINUTE);
      const response = await listProjects(cookie);
      expect(response.status, `at minute ${String(minute)}`).toBe(200);
      // The browser is told nothing: the cookie it holds is the same cookie.
      expect(response.headers.getSetCookie()).toEqual([]);
    }

    // Six requests, six renewals (every gap is far more than ten minutes), and each request was
    // forwarded with the credential its own renewal had just put in the row.
    expect(renewCalls).toEqual(['Bearer cred-1', 'Bearer cred-2', 'Bearer cred-3', 'Bearer cred-4', 'Bearer cred-5', 'Bearer cred-6']);
    expect(forwarded.map((call) => call.authorization)).toEqual([
      'Bearer cred-2', 'Bearer cred-3', 'Bearer cred-4', 'Bearer cred-5', 'Bearer cred-6', 'Bearer cred-7',
    ]);
    expect(credentialOf(id)).toBe('cred-7');
    // The same row: `openedAt` is kept and the credential's expiry has moved to the renewal.
    expect(subjectOf(id)?.openedAt).toBe(opened);
    expect(subjectOf(id)?.expiresAt).toBe(T0 + 300 * MINUTE + API_LIFETIME_MS);
  });

  it('outlives the credential it signed in with: 24 requests over 20 hours', async () => {
    // Five hours (above) fits inside one 8 h 10 min credential and proves no more than the
    // credential's own length. Twenty hours does not: without renewal the first credential is
    // refused by the API at 8 h 10 min, and every request after it is a 401.
    const { cookie } = await signIn();
    for (let minute = 50; minute <= 20 * 60; minute += 50) {
      at(minute * MINUTE);
      const response = await listProjects(cookie);
      expect(response.status, `at minute ${String(minute)}`).toBe(200);
    }
    expect(accepted.get('cred-1')).toBeLessThan(T0 + 20 * HOUR);
    expect(openSessionCount()).toBe(1);
  });

  it('renews on the first request that finds the credential more than 600 s old, and not before', async () => {
    expect(RENEW_AFTER_SECONDS).toBe(600);
    const { cookie } = await signIn();

    at(9 * MINUTE);
    await listProjects(cookie);
    expect(renewCalls).toHaveLength(0);

    at(10 * MINUTE); // exactly 600 s: not yet "more than"
    await listProjects(cookie);
    expect(renewCalls).toHaveLength(0);

    at(10 * MINUTE + SECOND);
    await listProjects(cookie);
    expect(renewCalls).toEqual(['Bearer cred-1']);

    // The renewal restarted the clock: five minutes later nothing is due.
    at(15 * MINUTE);
    await listProjects(cookie);
    expect(renewCalls).toHaveLength(1);
  });

  it('is told apart from the sign-in cookie: it lives as long as the cap, not the credential', async () => {
    const { lines } = await signIn();
    const session = lines.find((line) => line.startsWith('am_session='));
    const note = lines.find((line) => line.startsWith('am_session_note='));
    expect(session).toContain(`Max-Age=${String(SESSION_ABSOLUTE_CAP_SECONDS)}`);
    expect(SESSION_ABSOLUTE_CAP_SECONDS).toBe(30 * 24 * 3600);
    // The `open` note is the cap plus its existing week of grace.
    expect(note).toContain(`Max-Age=${String(SESSION_ABSOLUTE_CAP_SECONDS + 7 * 24 * 3600)}`);
  });
});

describe('idle: no request for the window ends the session as «истёк»', () => {
  it('no request for more than 8 h 10 min sends the reviewer to sign-in with reason expired', async () => {
    const { cookie, id } = await signIn();

    at(API_LIFETIME_MS + SECOND);
    const response = await listProjects(cookie);

    expect(response.status).toBe(401);
    expect(forwarded).toHaveLength(0);
    expect(renewCalls).toHaveLength(0);
    expect(openSessionCount()).toBe(0);
    const lines = response.headers.getSetCookie();
    // The session cookie is cleared, and no `invalid` note is written over the `open` one:
    // this is an expired session and not a forged identifier.
    expect(lines.some((line) => line.startsWith('am_session=;') && line.includes('Max-Age=0'))).toBe(true);
    expect(lines.some((line) => line.includes('am_session_note='))).toBe(false);

    // The sign-in screen, asked with the cookie the browser still holds: expired.
    expect(sessionLapsed(id)).toBe(true);
    expect(guestSessionReasonFromHeader(cookie)).toBe('expired');
    // And asked once the browser has applied the clearing, with the `open` note it kept.
    expect(guestSessionReasonFromHeader('am_session_note=open')).toBe('expired');
  });

  it('an identifier this register never held is still `invalid`, not `expired`', async () => {
    const forged = `am_session=${'ab'.repeat(32)}`;
    expect(guestSessionReasonFromHeader(forged)).toBe('invalid');
    expect(guestSessionReasonFromHeader(`${forged}; am_session_note=open`)).toBe('invalid');
  });

  it('is alive 7 h 59 m 59 s after a request that did not renew: the arithmetic of the two numbers', async () => {
    const { cookie } = await signIn();
    at(9 * MINUTE); // inside the cadence: no renewal, so the credential is 9 minutes old
    expect((await listProjects(cookie)).status).toBe(200);
    expect(renewCalls).toHaveLength(0);

    // 8 hours of silence less a second after that request: the credential, 8 h 10 min from
    // sign-in, is still good by 1 min 1 s, which is why the lifetime carries the extra ten.
    at(9 * MINUTE + 8 * HOUR - SECOND);
    const response = await listProjects(cookie);
    expect(response.status).toBe(200);
    expect(renewCalls).toEqual(['Bearer cred-1']);
  });

  it('a lapsed id survives a restart, so «истёк» does not turn into «недействителен»', async () => {
    storeDirectory = mkdtempSync(join(tmpdir(), 'renew1118-'));
    process.env.AUDITMANAGER_SESSION_STORE = join(storeDirectory, 'sessions.json');
    forgetEverySession();
    const { cookie } = await signIn();

    at(API_LIFETIME_MS + SECOND);
    expect((await listProjects(cookie)).status).toBe(401);

    dropTheInMemoryRegister(); // what a deploy does: the next read comes from the volume
    expect(guestSessionReasonFromHeader(cookie)).toBe('expired');
  });

  it('a lapse the process slept through is still «истёк»: the row is read, found ended, remembered', async () => {
    storeDirectory = mkdtempSync(join(tmpdir(), 'renew1118-'));
    process.env.AUDITMANAGER_SESSION_STORE = join(storeDirectory, 'sessions.json');
    forgetEverySession();
    const { cookie } = await signIn();

    dropTheInMemoryRegister(); // restart with the row on the volume ...
    at(API_LIFETIME_MS + SECOND); // ... and the credential dies while nothing is running
    expect(guestSessionReasonFromHeader(cookie)).toBe('expired');
  });
});

describe('the absolute cap: thirty days from sign-in, however active', () => {
  it('past 30 days there is no renewal and the session has ended', async () => {
    const { cookie, id } = await signIn();

    // Active every 8 hours for 29 days and 23 hours: every request renews, none is refused.
    for (let step = 1; T0 + step * 8 * HOUR < T0 + 30 * DAY - HOUR; step += 1) {
      at(step * 8 * HOUR);
      const response = await listProjects(cookie);
      expect(response.status, `at hour ${String(step * 8)}`).toBe(200);
    }
    at(30 * DAY - MINUTE); // a minute inside the cap: still renewed
    expect((await listProjects(cookie)).status).toBe(200);
    const renewalsInsideTheCap = renewCalls.length;
    expect(renewalsInsideTheCap).toBeGreaterThan(80);
    const lastCredential = credentialOf(id) as string;
    // The credential in the row is good for hours more: it is the cap that ends the session.
    expect(accepted.get(lastCredential)).toBeGreaterThan(T0 + 30 * DAY + HOUR);

    at(30 * DAY + SECOND);
    const response = await listProjects(cookie);

    expect(response.status).toBe(401);
    expect(renewCalls).toHaveLength(renewalsInsideTheCap); // no renewal past the cap
    expect(openSessionCount()).toBe(0);
    expect(subjectOf(id)).toBeNull();
    expect(remainingCapSeconds(id)).toBe(0);
    expect(guestSessionReasonFromHeader(cookie)).toBe('expired');
  });

  it('a row at its cap is never due for renewal, whatever the age of its credential', () => {
    const id = openSession(ACCOUNT, 'held', API_LIFETIME_SECONDS, T0);
    expect(renewalDue(id, T0 + 11 * MINUTE)).toBe(true);
    expect(renewalDue(id, T0 + 30 * DAY + SECOND)).toBe(false);
    expect(credentialOf(id, T0 + 30 * DAY + SECOND)).toBeNull();
  });

  it('counts the cap down: the cookie of a password change is the remaining cap, not a lifetime', () => {
    const id = openSession(ACCOUNT, 'held', API_LIFETIME_SECONDS, T0);
    expect(remainingCapSeconds(id, T0)).toBe(30 * 24 * 3600);
    // A few milliseconds later it still says the whole cap: the cookie is not a function of the clock.
    expect(remainingCapSeconds(id, T0 + 3)).toBe(30 * 24 * 3600);
    expect(remainingCapSeconds(id, T0 + 5 * HOUR)).toBe(30 * 24 * 3600 - 5 * 3600);
    expect(remainingCapSeconds('0'.repeat(64), T0)).toBe(0); // no such session: delete the cookie
  });
});

describe('one renewal per session at a time', () => {
  it('5 concurrent requests make exactly one renew call', async () => {
    const { cookie } = await signIn();
    at(HOUR);
    let release: () => void = () => undefined;
    renewGate = new Promise<void>((resolve) => {
      release = resolve;
    });

    const pending = Array.from({ length: 5 }, () => listProjects(cookie));
    // Let all five reach the renewal before the API answers the one that is in flight.
    await new Promise((resolve) => setTimeout(resolve, 20));
    release();
    const responses = await Promise.all(pending);

    expect(responses.map((response) => response.status)).toEqual([200, 200, 200, 200, 200]);
    expect(renewCalls).toEqual(['Bearer cred-1']);
    // All five went on with the one renewed credential.
    expect(forwarded.map((call) => call.authorization)).toEqual(Array(5).fill('Bearer cred-2'));
  });

  it('a refused renewal is shared too: one call, five sessions-ended answers, each its own body', async () => {
    const { cookie } = await signIn();
    at(HOUR);
    renewMode = 'unauthorized';
    let release: () => void = () => undefined;
    renewGate = new Promise<void>((resolve) => {
      release = resolve;
    });

    const pending = Array.from({ length: 5 }, () => listProjects(cookie));
    await new Promise((resolve) => setTimeout(resolve, 20));
    release();
    const responses = await Promise.all(pending);

    expect(renewCalls).toHaveLength(1);
    expect(responses.map((response) => response.status)).toEqual([401, 401, 401, 401, 401]);
    // A `Response` body can be read once: each caller was handed a body of its own.
    for (const response of responses) {
      expect(((await response.json()) as { correlation_id: string }).correlation_id).toBe('api-renew-401');
    }
  });
});

describe('the API refuses the renewal, or cannot be asked', () => {
  it('a 401 on renew closes the session as an upstream 401 does, with the API envelope', async () => {
    const { cookie, id } = await signIn();
    at(HOUR);
    renewMode = 'unauthorized';

    const response = await listProjects(cookie);

    expect(response.status).toBe(401);
    expect(((await response.json()) as { correlation_id: string }).correlation_id).toBe('api-renew-401');
    expect(forwarded).toHaveLength(0); // the request itself was never sent
    expect(subjectOf(id)).toBeNull();
    expect(openSessionCount()).toBe(0);
    const lines = response.headers.getSetCookie();
    expect(lines.some((line) => line.startsWith('am_session=;') && line.includes('Max-Age=0'))).toBe(true);
    expect(lines.some((line) => line.startsWith('am_session_note=ended'))).toBe(true);
    // Never the held credential in any header or body that goes back to the browser.
    expect(JSON.stringify([...response.headers])).not.toContain('cred-1');
  });

  it('a 5xx on renew forwards with the old credential, keeps the session, and logs one line', async () => {
    const { cookie, id } = await signIn();
    at(HOUR);
    renewMode = 'unavailable';

    const response = await listProjects(cookie);

    expect(response.status).toBe(200);
    expect(forwarded.map((call) => call.authorization)).toEqual(['Bearer cred-1']);
    expect(subjectOf(id)).not.toBeNull();
    expect(credentialOf(id)).toBe('cred-1');
    expect(warnings).toHaveLength(1);
    expect(warnings[0]).toContain('renewToken failed');
    expect(warnings[0]).toContain('HTTP 503');
    expect(warnings[0]).not.toContain('cred-1'); // the credential is never logged

    // The API recovers: the very next request asks again and the session slides on.
    renewMode = 'ok';
    at(HOUR + MINUTE);
    expect((await listProjects(cookie)).status).toBe(200);
    expect(renewCalls).toEqual(['Bearer cred-1', 'Bearer cred-1']);
    expect(credentialOf(id)).toBe('cred-2');
    expect(warnings).toHaveLength(1);
  });

  it('an API that cannot be reached is the same degradation: forwarded, kept, one line', async () => {
    const { cookie, id } = await signIn();
    at(HOUR);
    renewMode = 'unreachable';

    const response = await listProjects(cookie);

    // The upstream forward itself succeeds (the stub throws only on the renewal path) ...
    expect(response.status).toBe(200);
    expect(forwarded.map((call) => call.authorization)).toEqual(['Bearer cred-1']);
    expect(subjectOf(id)).not.toBeNull();
    expect(warnings).toHaveLength(1);
  });

  it('a 200 that is not a credential this tier will hold is a degradation too, never a session change', async () => {
    const { cookie, id } = await signIn();
    at(HOUR);
    vi.stubGlobal('fetch', async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = new URL(String(input)).pathname;
      if (path === '/auth/token/renew') {
        renewCalls.push('Bearer cred-1');
        return json({ token: 'cred-x', expires_in: 5, is_default_credential: false });
      }
      return respond(path, init?.method ?? 'GET', new Headers(init?.headers ?? {}).get('authorization'));
    });

    expect((await listProjects(cookie)).status).toBe(200);
    expect(credentialOf(id)).toBe('cred-1');
    expect(warnings).toHaveLength(1);
  });
});

describe('a row from before the sliding session', () => {
  it('without credentialIssuedAt is due on first use, and renews', async () => {
    storeDirectory = mkdtempSync(join(tmpdir(), 'renew1118-'));
    const file = join(storeDirectory, 'sessions.json');
    process.env.AUDITMANAGER_SESSION_STORE = file;
    forgetEverySession();

    // A row as the code before this change wrote it: everything but the new field.
    accepted.set('legacy-cred', T0 + API_LIFETIME_MS);
    const id = openSession(ACCOUNT, 'legacy-cred', API_LIFETIME_SECONDS, T0);
    const written = JSON.parse(readFileSync(file, 'utf8')) as {
      sessions: Record<string, unknown>[];
    };
    for (const row of written.sessions) delete row.credentialIssuedAt;
    writeFileSync(file, JSON.stringify(written));
    dropTheInMemoryRegister();

    // One minute after sign-in: a row that knew its age would not be due. This one does not.
    at(MINUTE);
    expect(renewalDue(id, T0 + MINUTE)).toBe(true);
    const response = await listProjects(`am_session=${id}`);

    expect(response.status).toBe(200);
    expect(renewCalls).toEqual(['Bearer legacy-cred']);
    expect(forwarded.map((call) => call.authorization)).toEqual(['Bearer cred-1']);
    // And now it has an issue time of its own, a real one: not due a minute later.
    expect(renewalDue(id, T0 + 2 * MINUTE)).toBe(false);
  });

  it('a row that carries its issue time is not due before 600 s', () => {
    const id = openSession(ACCOUNT, 'held', API_LIFETIME_SECONDS, T0);
    expect(renewalDue(id, T0 + 10 * MINUTE)).toBe(false);
    expect(renewalDue(id, T0 + 10 * MINUTE + 1)).toBe(true);
  });
});
