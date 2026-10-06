/**
 * `W49-QA-01`, item 8 (BFF half) — the status at sign-in, the rejected pair, and the throttle.
 *
 * `W49-PLAN.md` §3.5 and `R-56` with its 2026-10-06 addendum: "On a failed exchange the session
 * handler calls `readRegistrationStatus` with the same pair; a `pending` answer sends the
 * browser to `/login?refusal=pending`, anything else to the generic `credentials` refusal."
 * "A rejected applicant sees nothing at sign-in." And the guest throttle: a per-client bucket on
 * `POST /bff/v1/session` refuses with `303` to `/login?refusal=throttled`, keyed by `X-Real-IP`
 * only under `AUDITMANAGER_BEHIND_PROXY=1`, one shared bucket without it, never by
 * `X-Forwarded-For`; and the catch-all refuses the status read itself to the browser, so the
 * bucket cannot be walked around.
 *
 * The API half of the item is `tests/integration/api/qa_w49/test_qa_w49_status_read.py`.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { POST } from '@/app/bff/v1/[...path]/route';
import { GUEST_BUCKET_CAPACITY, forgetEveryGuestBucket } from '@/app/bff/session/guest-throttle';
import { forgetEverySession, openSessionCount } from '@/app/bff/session/store';

const UPSTREAM = 'http://api.qa49:8000';
const DEPLOYMENT_TOKEN = 'qa49-deployment-signing-input';
const LOGIN = 'applicant@qa.invalid';
const PASSWORD = 'qa49-applicant-password';

interface Seen {
  readonly path: string;
  readonly method: string;
  readonly body: string;
}

let seen: Seen[] = [];
/** What `readRegistrationStatus` answers this test. */
let status: () => Response;

const GENERIC_401 = JSON.stringify({
  contract_version: '1.0.0-draft.1',
  correlation_id: 'qa49-generic-401',
  error_code: 'authentication_required',
  message: 'The credential is not accepted.',
  retryable: false,
});

function generic401(): Response {
  return new Response(GENERIC_401, {
    status: 401,
    headers: { 'content-type': 'application/json', 'x-correlation-id': 'qa49-generic-401' },
  });
}

function json(body: unknown, statusCode = 200): Response {
  return new Response(JSON.stringify(body), {
    status: statusCode,
    headers: { 'content-type': 'application/json' },
  });
}

const ORIGINAL = {
  upstream: process.env.AUDITMANAGER_API_UPSTREAM,
  token: process.env.AUDITMANAGER_API_TOKEN,
  proxy: process.env.AUDITMANAGER_BEHIND_PROXY,
};

beforeEach(() => {
  forgetEverySession();
  forgetEveryGuestBucket();
  seen = [];
  status = generic401;
  process.env.AUDITMANAGER_API_UPSTREAM = UPSTREAM;
  process.env.AUDITMANAGER_API_TOKEN = DEPLOYMENT_TOKEN;
  delete process.env.AUDITMANAGER_BEHIND_PROXY;
  vi.stubGlobal('fetch', async (input: RequestInfo | URL, init?: RequestInit) => {
    const raw = init?.body;
    const method = init?.method ?? 'GET';
    const path = new URL(String(input)).pathname;
    seen.push({
      path,
      method,
      body:
        raw === undefined || raw === null
          ? ''
          : typeof raw === 'string'
            ? raw
            : new TextDecoder().decode(raw as ArrayBuffer),
    });
    // Every exchange in this file is refused: no account holds the pair.
    if (method === 'POST' && path === '/auth/token') return generic401();
    if (method === 'POST' && path === '/registrations/status') return status();
    return json({ items: [], next_cursor: null });
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  forgetEverySession();
  forgetEveryGuestBucket();
  for (const [name, value] of [
    ['AUDITMANAGER_API_UPSTREAM', ORIGINAL.upstream],
    ['AUDITMANAGER_API_TOKEN', ORIGINAL.token],
    ['AUDITMANAGER_BEHIND_PROXY', ORIGINAL.proxy],
  ] as const) {
    if (value === undefined) delete process.env[name];
    else process.env[name] = value;
  }
});

function signIn(headers: Record<string, string> = {}, login = LOGIN): Promise<Response> {
  return POST(
    new Request('http://web.qa49/bff/v1/session', {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded', ...headers },
      body: new URLSearchParams({ login, password: PASSWORD }).toString(),
    }),
    { params: Promise.resolve({ path: ['session'] }) },
  );
}

/** Everything a browser can observe about a redirect: status, every header, the body. */
async function observable(response: Response): Promise<[number, [string, string][], string]> {
  const headers = [...response.headers.entries()].sort(([a], [b]) => a.localeCompare(b));
  return [response.status, headers, await response.text()];
}

describe('W49-QA-01 item 8: what sign-in says about an application', () => {
  it('a pair proving a pending application lands on refusal=pending, opens nothing', async () => {
    status = () => json({ status: 'pending' });
    const response = await signIn();
    expect(response.status).toBe(303);
    expect(response.headers.get('location')).toBe('/login?refusal=pending');
    expect(response.headers.get('set-cookie')).toBeNull();
    expect(openSessionCount()).toBe(0);
    // The exchange first, then the status read with the very same pair; nothing else.
    expect(seen.map((entry) => `${entry.method} ${entry.path}`)).toEqual([
      'POST /auth/token',
      'POST /registrations/status',
    ]);
    expect(JSON.parse(seen[1]?.body ?? '{}')).toEqual({ login: LOGIN, password: PASSWORD });
  });

  it('a rejected pair is observably the same as an unknown pair: the generic credentials refusal', async () => {
    // The API answers both with its one generic 401 (the decision nulled the password).
    status = generic401;
    const rejected = await observable(await signIn());
    forgetEveryGuestBucket();
    const unknown = await observable(await signIn({}, 'nobody@qa.invalid'));
    expect(rejected).toEqual(unknown);
    expect(rejected[0]).toBe(303);
    expect(rejected[1]).toContainEqual(['location', '/login?refusal=credentials']);
    expect(rejected[1].some(([name]) => name === 'set-cookie')).toBe(false);
  });

  it.each([
    ['a 200 naming rejected', () => json({ status: 'rejected', rejection_reason: 'Нет.' })],
    ['a 200 naming approved', () => json({ status: 'approved' })],
    ['a 200 with no status', () => json({})],
    ['a 200 that is not JSON', () => new Response('pending', { status: 200 })],
    ['a 429 from a proxy', () => json({ error_code: 'rate_limited' }, 429)],
    ['a 500', () => json({ error_code: 'internal_error' }, 500)],
  ])('%s from the status read is the generic credentials refusal, never pending', async (_name, answer) => {
    status = answer;
    const response = await signIn();
    expect(response.headers.get('location')).toBe('/login?refusal=credentials');
    expect(response.headers.get('location')).not.toContain('Нет');
  });
});

describe('W49-QA-01 item 8: the throttle on those attempts', () => {
  it('without the proxy flag one bucket: the attempt past capacity is throttled and sends nothing', async () => {
    for (let attempt = 0; attempt < GUEST_BUCKET_CAPACITY; attempt += 1) {
      const admitted = await signIn({ 'x-real-ip': `198.51.100.${attempt}` });
      expect(admitted.headers.get('location')).toBe('/login?refusal=credentials');
    }
    expect(seen).toHaveLength(2 * GUEST_BUCKET_CAPACITY);
    seen = [];
    // A different X-Real-IP does not help when no proxy is trusted.
    const throttled = await signIn({ 'x-real-ip': '203.0.113.77' });
    expect(throttled.status).toBe(303);
    expect(throttled.headers.get('location')).toBe('/login?refusal=throttled');
    expect(seen).toEqual([]);
  });

  it('behind the proxy the bucket is the X-Real-IP, and a forged X-Forwarded-For does not escape it', async () => {
    process.env.AUDITMANAGER_BEHIND_PROXY = '1';
    const client = { 'x-real-ip': '192.0.2.10' };
    for (let attempt = 0; attempt < GUEST_BUCKET_CAPACITY; attempt += 1) {
      await signIn({ ...client, 'x-forwarded-for': `10.0.0.${attempt}` });
    }
    seen = [];
    const forged = await signIn({ ...client, 'x-forwarded-for': '10.9.9.9, 192.0.2.250' });
    expect(forged.headers.get('location')).toBe('/login?refusal=throttled');
    expect(seen).toEqual([]);

    const neighbour = await signIn({ 'x-real-ip': '192.0.2.11' });
    expect(neighbour.headers.get('location')).toBe('/login?refusal=credentials');
  });

  it.each([
    ['without a session', {}],
    ['with a cookie', { cookie: `am_session=${'a'.repeat(64)}` }],
  ])('the status read cannot be reached around the bucket through the catch-all, %s', async (_name, headers) => {
    const response = await POST(
      new Request('http://web.qa49/bff/v1/registrations/status', {
        method: 'POST',
        headers: { 'content-type': 'application/json', ...headers },
        body: JSON.stringify({ login: LOGIN, password: PASSWORD }),
      }),
      { params: Promise.resolve({ path: ['registrations', 'status'] }) },
    );
    expect(response.status).toBe(404);
    expect(seen).toEqual([]);
  });
});
