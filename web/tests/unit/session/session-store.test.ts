/**
 * The register that holds a signed-in reviewer's credential.
 *
 * Two properties are worth a test here and the rest is bookkeeping:
 *
 *   1. **the credential has exactly one exit.** `subjectOf` is what a screen calls and it
 *      returns a login and two instants; `credentialOf` is what the forwarder calls and it
 *      is the only function in the module that returns the token. A future session adding
 *      the token to `SessionSubject` for convenience would put it in an RSC payload, and
 *      the payload is bytes the browser holds — so the shape of that record is asserted,
 *      not assumed.
 *   2. **an identifier that was not minted here reaches nothing.** The cookie is attacker
 *      input; anything outside the minted shape is treated as absent rather than looked up.
 */

import { beforeEach, describe, expect, it } from 'vitest';

import {
  MAX_LIFETIME_SECONDS,
  MIN_LIFETIME_SECONDS,
  SESSION_COOKIE,
  SESSION_ID_PATTERN,
  SessionLifetimeError,
  clearedSessionCookie,
  closeSession,
  credentialOf,
  forgetEverySession,
  mintSessionId,
  openSession,
  openSessionCount,
  readSessionId,
  requestIsSecure,
  sessionCookie,
  subjectOf,
} from '@/app/bff/session/store';

const CREDENTIAL = 'minted-token-9f3c';
const LOGIN = 'проверяющий';
const HOUR = 3600;

beforeEach(() => {
  forgetEverySession();
});

describe('a session is an opaque number here and a credential there', () => {
  it('mints identifiers of the declared shape, and never the same one twice', () => {
    const minted = new Set(Array.from({ length: 200 }, () => mintSessionId()));
    expect(minted.size).toBe(200);
    for (const id of minted) expect(SESSION_ID_PATTERN.test(id)).toBe(true);
  });

  it('hands the credential to the forwarder and to nothing else', () => {
    const id = openSession(LOGIN, CREDENTIAL, HOUR);
    expect(credentialOf(id)).toBe(CREDENTIAL);

    const subject = subjectOf(id);
    expect(subject).not.toBeNull();
    // The whole record, as a set of keys: a token added as a convenience field is red here
    // rather than discovered in a payload.
    expect(Object.keys(subject as object).sort()).toEqual(['expiresAt', 'login', 'openedAt']);
    expect(JSON.stringify(subject)).not.toContain(CREDENTIAL);
  });

  it('treats an unminted, malformed or absent identifier as no session at all', () => {
    openSession(LOGIN, CREDENTIAL, HOUR);
    for (const bogus of [null, '', 'нет', 'a'.repeat(64), '00', `${'0'.repeat(63)}g`]) {
      expect(subjectOf(bogus)).toBeNull();
      expect(credentialOf(bogus)).toBeNull();
      expect(closeSession(bogus)).toBe(false);
    }
  });

  it('forgets a session the moment it expires, on both readers', () => {
    const opened = 1_000_000;
    const id = openSession(LOGIN, CREDENTIAL, MIN_LIFETIME_SECONDS, opened);
    const alive = opened + (MIN_LIFETIME_SECONDS - 1) * 1000;
    const dead = opened + MIN_LIFETIME_SECONDS * 1000;

    expect(credentialOf(id, alive)).toBe(CREDENTIAL);
    expect(subjectOf(id, alive)).not.toBeNull();
    expect(credentialOf(id, dead)).toBeNull();
    expect(subjectOf(id, dead)).toBeNull();
    expect(openSessionCount(dead)).toBe(0);
  });

  it('ends a session on request, and the identifier then opens nothing', () => {
    const id = openSession(LOGIN, CREDENTIAL, HOUR);
    expect(openSessionCount()).toBe(1);
    expect(closeSession(id)).toBe(true);
    expect(closeSession(id)).toBe(false);
    expect(credentialOf(id)).toBeNull();
    expect(openSessionCount()).toBe(0);
  });

  it('refuses a lifetime it would have to guess at, rather than defaulting one', () => {
    for (const bad of [0, -1, MIN_LIFETIME_SECONDS - 1, MAX_LIFETIME_SECONDS + 1, Number.NaN, Infinity]) {
      expect(() => openSession(LOGIN, CREDENTIAL, bad)).toThrow(SessionLifetimeError);
    }
    expect(() => openSession(LOGIN, '   ', HOUR)).toThrow(SessionLifetimeError);
    expect(openSessionCount()).toBe(0);
  });

  it('keeps two reviewers apart', () => {
    const first = openSession('первый', 'token-a', HOUR);
    const second = openSession('второй', 'token-b', HOUR);
    expect(first).not.toBe(second);
    expect(credentialOf(first)).toBe('token-a');
    expect(credentialOf(second)).toBe('token-b');
    closeSession(first);
    expect(credentialOf(second)).toBe('token-b');
  });
});

describe('the cookie carries the number and nothing else', () => {
  it('is HttpOnly, same-site and lifetime-bound, so no script on the page can read it', () => {
    const id = mintSessionId();
    const value = sessionCookie(id, HOUR, false);
    expect(value).toContain(`${SESSION_COOKIE}=${id}`);
    expect(value).toContain('HttpOnly');
    expect(value).toContain('SameSite=Strict');
    expect(value).toContain('Path=/');
    expect(value).toContain(`Max-Age=${HOUR}`);
    expect(value).not.toContain('Secure');
    expect(sessionCookie(id, HOUR, true)).toContain('Secure');
  });

  it('clears by expiry rather than by writing a blank a browser would keep', () => {
    const cleared = clearedSessionCookie(false);
    expect(cleared).toContain(`${SESSION_COOKIE}=`);
    expect(cleared).toContain('Max-Age=0');
    expect(cleared).toContain('HttpOnly');
  });

  it('reads the identifier out of a header carrying several cookies', () => {
    const id = mintSessionId();
    expect(readSessionId(`theme=dark; ${SESSION_COOKIE}=${id}; other=1`)).toBe(id);
    expect(readSessionId(`${SESSION_COOKIE}=${id}`)).toBe(id);
    expect(readSessionId(null)).toBeNull();
    expect(readSessionId('theme=dark')).toBeNull();
    // A value that is not the minted shape never becomes a lookup key.
    expect(readSessionId(`${SESSION_COOKIE}=../../etc/passwd`)).toBeNull();
    expect(readSessionId(`${SESSION_COOKIE}=`)).toBeNull();
  });

  it('marks the cookie Secure from what the proxy says, not from what this process sees', () => {
    const plain = new Request('http://web.test/bff/v1/session', { method: 'POST' });
    const behindTls = new Request('http://web.test/bff/v1/session', {
      method: 'POST',
      headers: { 'x-forwarded-proto': 'https, http' },
    });
    const direct = new Request('https://web.test/bff/v1/session', { method: 'POST' });
    expect(requestIsSecure(plain)).toBe(false);
    expect(requestIsSecure(behindTls)).toBe(true);
    expect(requestIsSecure(direct)).toBe(true);
  });
});
