/**
 * The guest throttle, driven through the real route handler: whose bucket a request spends
 * from, when it is empty, and what the form is told.
 *
 * `W49-PLAN.md` §3.5 names three properties and each has a case here that a broken key or a
 * broken count turns red:
 *
 *   1. **the bucket refuses the N+1th guest request within the window** — and refuses it before
 *      the form is read or anything is sent;
 *   2. **a forged `X-Forwarded-For` does not escape it** — the key is `X-Real-IP`, which the
 *      proxy *sets*, and `X-Forwarded-For` is never read;
 *   3. **without `AUDITMANAGER_BEHIND_PROXY=1` the bucket is global** — `X-Real-IP` is then a
 *      header any client could write, so every request shares one bucket.
 *
 * The clock is vitest's fake one, so "within the window" is an instant this suite chooses
 * rather than a race against the machine.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { POST } from '@/app/bff/v1/[...path]/route';
import {
  GUEST_BUCKET_CAPACITY,
  GUEST_BUCKET_REFILL_MS,
  MAX_TRACKED_CLIENTS,
  SHARED_BUCKET_KEY,
  UNIDENTIFIED_BUCKET_KEY,
  admitGuest,
  forgetEveryGuestBucket,
  guestClientKey,
  trackedGuestCount,
} from '@/app/bff/session/guest-throttle';
import { forgetEverySession } from '@/app/bff/session/store';
import { BEHIND_PROXY_VARIABLE, isBehindProxy } from '@/shared/config/proxy-trust';
import { signInRefusalUrl } from '@/features/sign-in';

import { authenticationRequired } from './account-fixture';

const UPSTREAM = 'http://api.test:8000';
const ORIGINAL = {
  upstream: process.env.AUDITMANAGER_API_UPSTREAM,
  token: process.env.AUDITMANAGER_API_TOKEN,
  proxy: process.env[BEHIND_PROXY_VARIABLE],
};

let sent: string[] = [];

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date('2026-10-06T09:00:00.000Z'));
  forgetEverySession();
  forgetEveryGuestBucket();
  sent = [];
  process.env.AUDITMANAGER_API_UPSTREAM = UPSTREAM;
  process.env.AUDITMANAGER_API_TOKEN = 'deployment-credential-a1b2';
  delete process.env[BEHIND_PROXY_VARIABLE];
  // Every exchange is refused and every status read says nothing: the cheapest honest
  // answers, so each admitted request is visible upstream and none opens a session.
  vi.stubGlobal('fetch', async (input: RequestInfo | URL) => {
    sent.push(new URL(String(input)).pathname);
    return authenticationRequired();
  });
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  forgetEverySession();
  forgetEveryGuestBucket();
  for (const [name, value] of [
    ['AUDITMANAGER_API_UPSTREAM', ORIGINAL.upstream],
    ['AUDITMANAGER_API_TOKEN', ORIGINAL.token],
    [BEHIND_PROXY_VARIABLE, ORIGINAL.proxy],
  ] as const) {
    if (value === undefined) delete process.env[name];
    else process.env[name] = value;
  }
});

/** A sign-in post, carrying whatever client headers the case wants. */
function signIn(headers: Record<string, string> = {}, form = 'login=a&password=b'): Promise<Response> {
  return POST(
    new Request('http://web.test/bff/v1/session', {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded', ...headers },
      body: form,
    }),
    { params: Promise.resolve({ path: ['session'] }) },
  );
}

function apply(headers: Record<string, string> = {}): Promise<Response> {
  return POST(
    new Request('http://web.test/bff/v1/registration', {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded', ...headers },
      body: 'login=a%40b.c&password=p&confirm_password=p&last_name=%D0%90&first_name=%D0%91',
    }),
    { params: Promise.resolve({ path: ['registration'] }) },
  );
}

const THROTTLED = signInRefusalUrl('throttled');

async function isThrottled(response: Promise<Response>): Promise<boolean> {
  return (await response).headers.get('location') === THROTTLED;
}

/** Spend a whole bucket from one client and assert every request was admitted. */
async function spendTheBucket(headers: Record<string, string>): Promise<void> {
  for (let index = 0; index < GUEST_BUCKET_CAPACITY; index += 1) {
    expect(await isThrottled(signIn(headers)), `request ${index + 1} of ${GUEST_BUCKET_CAPACITY}`).toBe(
      false,
    );
  }
}

describe('the bucket holds N requests, and refuses the N+1th within the window', () => {
  it('admits N guests at one instant and refuses the next, before anything is sent', async () => {
    process.env[BEHIND_PROXY_VARIABLE] = '1';
    const client = { 'x-real-ip': '198.51.100.7' };
    await spendTheBucket(client);
    const before = sent.length;

    const refused = await signIn(client);
    expect(refused.status).toBe(303);
    expect(refused.headers.get('location')).toBe(THROTTLED);
    expect(refused.headers.get('set-cookie')).toBeNull();
    expect(await refused.text()).toBe('');
    // Refused before the form was read and before the API was asked anything.
    expect(sent.length).toBe(before);
  });

  it('refuses even a malformed form once the bucket is empty: the bucket is asked first', async () => {
    process.env[BEHIND_PROXY_VARIABLE] = '1';
    const client = { 'x-real-ip': '198.51.100.7' };
    await spendTheBucket(client);
    expect(await isThrottled(signIn(client, 'not=a&form=for+sign-in'))).toBe(true);
  });

  it('gives one request back per refill interval, and no more', async () => {
    process.env[BEHIND_PROXY_VARIABLE] = '1';
    const client = { 'x-real-ip': '198.51.100.7' };
    await spendTheBucket(client);
    expect(await isThrottled(signIn(client))).toBe(true);

    vi.advanceTimersByTime(GUEST_BUCKET_REFILL_MS - 1);
    expect(await isThrottled(signIn(client))).toBe(true);
    vi.advanceTimersByTime(1);
    expect(await isThrottled(signIn(client))).toBe(false);
    expect(await isThrottled(signIn(client))).toBe(true);
  });

  it('spends the same bucket on the registration door, which answers its own screen', async () => {
    process.env[BEHIND_PROXY_VARIABLE] = '1';
    const client = { 'x-real-ip': '198.51.100.7' };
    await spendTheBucket(client);
    const refused = await apply(client);
    expect(refused.status).toBe(303);
    expect(refused.headers.get('location')).toBe('/register?refusal=throttled');
    expect(sent.filter((path) => path === '/registrations')).toEqual([]);
  });

  it('throttles only the two guest doors: a signed-out read is not a guest post', async () => {
    process.env[BEHIND_PROXY_VARIABLE] = '1';
    const client = { 'x-real-ip': '198.51.100.7' };
    await spendTheBucket(client);
    const end = await POST(
      new Request('http://web.test/bff/v1/session/end', { method: 'POST', headers: client }),
      { params: Promise.resolve({ path: ['session', 'end'] }) },
    );
    expect(end.headers.get('location')).toBe('/login');
  });
});

describe('behind the proxy, the key is X-Real-IP and nothing a client can choose', () => {
  it('keeps two clients apart', async () => {
    process.env[BEHIND_PROXY_VARIABLE] = '1';
    await spendTheBucket({ 'x-real-ip': '198.51.100.7' });
    expect(await isThrottled(signIn({ 'x-real-ip': '198.51.100.7' }))).toBe(true);
    expect(await isThrottled(signIn({ 'x-real-ip': '203.0.113.9' }))).toBe(false);
  });

  it('does not let a forged X-Forwarded-For escape the bucket', async () => {
    process.env[BEHIND_PROXY_VARIABLE] = '1';
    // nginx appends the peer to X-Forwarded-For and keeps whatever the client wrote first;
    // X-Real-IP it SETS. So every request below is the same client, whatever it claims.
    for (let index = 0; index < GUEST_BUCKET_CAPACITY; index += 1) {
      await signIn({
        'x-real-ip': '198.51.100.7',
        'x-forwarded-for': `10.0.${index}.1, 198.51.100.7`,
      });
    }
    for (const forged of ['10.9.9.9', '203.0.113.9, 198.51.100.7', '::1']) {
      expect(
        await isThrottled(signIn({ 'x-real-ip': '198.51.100.7', 'x-forwarded-for': forged })),
        forged,
      ).toBe(true);
    }
  });

  it('puts requests without an address in one shared bucket, not a fresh one each', async () => {
    process.env[BEHIND_PROXY_VARIABLE] = '1';
    for (let index = 0; index < GUEST_BUCKET_CAPACITY; index += 1) {
      await signIn({ 'x-forwarded-for': `10.0.${index}.1` });
    }
    expect(await isThrottled(signIn({ 'x-forwarded-for': '10.8.8.8' }))).toBe(true);
    expect(await isThrottled(signIn({ 'x-real-ip': '   ' }))).toBe(true);
  });

  it('reads the key from X-Real-IP alone', () => {
    const request = new Request('http://web.test/', {
      headers: { 'x-real-ip': ' 198.51.100.7 ', 'x-forwarded-for': '10.0.0.1' },
    });
    expect(guestClientKey(request, true)).toBe('ip:198.51.100.7');
    expect(guestClientKey(new Request('http://web.test/'), true)).toBe(UNIDENTIFIED_BUCKET_KEY);
    expect(
      guestClientKey(new Request('http://web.test/', { headers: { 'x-real-ip': 'x'.repeat(65) } }), true),
    ).toBe(UNIDENTIFIED_BUCKET_KEY);
  });
});

describe('without the proxy flag, every guest shares one bucket', () => {
  it('counts different X-Real-IP values against one bucket', async () => {
    // Without the flag the header is something any client could write, so it is not a key.
    for (let index = 0; index < GUEST_BUCKET_CAPACITY; index += 1) {
      expect(await isThrottled(signIn({ 'x-real-ip': `198.51.100.${index}` }))).toBe(false);
    }
    expect(await isThrottled(signIn({ 'x-real-ip': '203.0.113.200' }))).toBe(true);
    expect(await isThrottled(signIn({}))).toBe(true);
  });

  it('treats any value but 1 as no flag, which can only make the throttle tighter', () => {
    for (const value of [undefined, '', '  ', '0', 'true', 'yes', '01', ' 1 ']) {
      if (value === undefined) delete process.env[BEHIND_PROXY_VARIABLE];
      else process.env[BEHIND_PROXY_VARIABLE] = value;
      expect(isBehindProxy(), JSON.stringify(value)).toBe(value?.trim() === '1');
    }
    const request = new Request('http://web.test/', { headers: { 'x-real-ip': '198.51.100.7' } });
    expect(guestClientKey(request, false)).toBe(SHARED_BUCKET_KEY);
  });
});

describe('the table that remembers clients is bounded', () => {
  it('forgets the least recently seen client past the bound, which then starts from a full bucket', () => {
    const now = Date.now();
    expect(admitGuest('ip:first', now)).toBe(true);
    for (let index = 0; index < MAX_TRACKED_CLIENTS; index += 1) admitGuest(`ip:${index}`, now);
    expect(trackedGuestCount()).toBe(MAX_TRACKED_CLIENTS);
    // `ip:first` was the least recently seen, so it is the one forgotten: a full bucket again.
    for (let index = 0; index < GUEST_BUCKET_CAPACITY; index += 1) {
      expect(admitGuest('ip:first', now)).toBe(true);
    }
    expect(admitGuest('ip:first', now)).toBe(false);
  });
});
