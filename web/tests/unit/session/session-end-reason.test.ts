/**
 * The sign-in screen says why there is no session: `/login?reason=expired|ended|invalid`.
 *
 * The original portal's sign-in page showed «Сеанс истёк», «Сеанс завершён» and «Сеанс
 * недействителен» from a `reason` in the address. Here the web tier's server side writes that
 * word where it genuinely knows the cause, and nowhere else:
 *
 *   - `ended`    the API refused a credential the register held as live (an administrator's
 *                «Завершить сеансы» raises the account's epoch; so do a changed password and
 *                changed rights): `endedOn`, and the executor-secret door's own `401`;
 *   - `invalid`  a request presented a session cookie that names no session here;
 *   - `expired`  no session cookie, and the `open` note the sign-in left — the cookie lapsed;
 *   - nothing    a first visit, a signed-out browser, a value outside the closed list.
 *
 * Four layers, each held on its own: the pure closed list and its sentences; the BFF doors
 * that write the note (real route handler, upstream stubbed by credential, a modelled
 * browser that keeps and drops cookies the way a browser does); the guard and the `/login`
 * route that read it back; and the markup. The end-to-end cases run the whole path — a
 * handler's `Set-Cookie` becomes the next request's `Cookie` — because the note is only worth
 * what survives that round trip.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { SignInPage } from '@/_pages/sign-in';
import { forgetEveryGuestBucket } from '@/app/bff/session/guest-throttle';
import {
  END_NOTE_LIFETIME_SECONDS,
  OPEN_NOTE_GRACE_SECONDS,
  SESSION_NOTES,
  SESSION_NOTE_COOKIE,
  clearedNoteCookie,
  endNoteCookie,
  guestSessionReason,
  guestSessionReasonFromHeader,
  openNoteCookie,
  readCookie,
  readSessionNote,
} from '@/app/bff/session/end-note';
import {
  SESSION_COOKIE,
  forgetEverySession,
  openSession,
  openSessionCount,
} from '@/app/bff/session/store';
import { POST, GET } from '@/app/bff/v1/[...path]/route';
import { SIGN_IN_REASON_PARAM, signInReasonMessage } from '@/features/sign-in';
import { screenAt } from '@/shared/config';
import {
  SESSION_END_REASONS,
  SESSION_END_REASON_PARAM,
  isSessionEndReason,
  sessionEndReasonOf,
} from '@/shared/lib/session-end-reason';

import { render } from '../review/fixtures';

import { accountAnswer } from './account-fixture';

/** The browser's cookies, by name — the guard and the `/login` route read this jar. */
const jar = vi.hoisted(() => ({ cookies: new Map<string, string>() }));

vi.mock('next/headers', () => ({
  cookies: async () => ({
    get: (name: string) => {
      const value = jar.cookies.get(name);
      return value === undefined ? undefined : { name, value };
    },
  }),
}));

const { enforceScreen } = await import('@/app/bff/session/screen-lock');
const { default: LoginRoute } = await import('@/app/login/page');

const UPSTREAM = 'http://api.reason.test:8000';
const DEPLOYMENT_TOKEN = 'deployment-credential-reason';
const LIFETIME = 3600;
const UNKNOWN_ID = 'a'.repeat(64);
const CONNECTION = 'exc_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';

// ============================================================ 1. the closed list, and its words

describe('the reason is one of three words, and anything else is no reason', () => {
  it('names exactly expired, ended and invalid, under the parameter `reason`', () => {
    expect([...SESSION_END_REASONS]).toEqual(['expired', 'ended', 'invalid']);
    expect(SESSION_END_REASON_PARAM).toBe('reason');
    expect(SIGN_IN_REASON_PARAM).toBe(SESSION_END_REASON_PARAM);
  });

  it('reads each of the three, the first of a repeated parameter, and nothing else', () => {
    for (const reason of SESSION_END_REASONS) expect(sessionEndReasonOf(reason)).toBe(reason);
    expect(sessionEndReasonOf(['ended', 'expired'])).toBe('ended');
    expect(sessionEndReasonOf(['nonsense', 'ended'])).toBeNull();
    for (const hostile of ['', 'boom', 'EXPIRED', ' ended', 'ended ', '<script>', 'session_expired', 'open', '__proto__']) {
      expect(sessionEndReasonOf(hostile), JSON.stringify(hostile)).toBeNull();
      expect(isSessionEndReason(hostile)).toBe(false);
    }
    expect(sessionEndReasonOf(undefined)).toBeNull();
    expect(sessionEndReasonOf(null)).toBeNull();
    expect(sessionEndReasonOf([])).toBeNull();
  });

  it('says each one in Russian, differently, with no Latin letter and a way forward', () => {
    const sentences = SESSION_END_REASONS.map((reason) => signInReasonMessage(reason));
    expect(new Set(sentences).size).toBe(3);
    expect(sentences).toEqual([
      'Сеанс истёк — войдите снова.',
      'Сеанс завершён — войдите снова.',
      'Сеанс недействителен — войдите снова.',
    ]);
    for (const sentence of sentences) expect(sentence).not.toMatch(/[A-Za-z]/);
  });
});

describe('the note: a closed word the browser keeps, never an identity', () => {
  it('knows exactly open, ended and invalid, and reads anything else as no note', () => {
    expect([...SESSION_NOTES]).toEqual(['open', 'ended', 'invalid']);
    for (const note of SESSION_NOTES) expect(readSessionNote(note)).toBe(note);
    for (const hostile of ['', 'expired', 'OPEN', 'boom', '<b>', undefined, null]) {
      expect(readSessionNote(hostile)).toBeNull();
    }
  });

  it('writes HttpOnly, SameSite=Strict cookies whose lifetimes are the ones argued for', () => {
    expect(openNoteCookie(LIFETIME, false)).toBe(
      `${SESSION_NOTE_COOKIE}=open; Path=/; HttpOnly; SameSite=Strict; Max-Age=${LIFETIME + OPEN_NOTE_GRACE_SECONDS}`,
    );
    expect(endNoteCookie('ended', false)).toBe(
      `${SESSION_NOTE_COOKIE}=ended; Path=/; HttpOnly; SameSite=Strict; Max-Age=${END_NOTE_LIFETIME_SECONDS}`,
    );
    expect(endNoteCookie('invalid', false)).toContain(`${SESSION_NOTE_COOKIE}=invalid;`);
    expect(clearedNoteCookie(false)).toBe(
      `${SESSION_NOTE_COOKIE}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0`,
    );
    for (const cookie of [openNoteCookie(LIFETIME, true), endNoteCookie('ended', true), clearedNoteCookie(true)]) {
      expect(cookie.endsWith('; Secure')).toBe(true);
    }
    // The grace is what lets a lapse be named a while after it, and an end note is short.
    expect(OPEN_NOTE_GRACE_SECONDS).toBeGreaterThan(24 * 60 * 60);
    expect(END_NOTE_LIFETIME_SECONDS).toBeLessThanOrEqual(15 * 60);
  });

  it('reads one cookie out of a Cookie header, and is not fooled by a longer name', () => {
    const header = `a=1; ${SESSION_NOTE_COOKIE}x=boom; ${SESSION_NOTE_COOKIE}=ended; ${SESSION_COOKIE}=${UNKNOWN_ID}`;
    expect(readCookie(header, SESSION_NOTE_COOKIE)).toBe('ended');
    expect(readCookie(header, SESSION_COOKIE)).toBe(UNKNOWN_ID);
    expect(readCookie(header, 'missing')).toBeNull();
    expect(readCookie(null, SESSION_COOKIE)).toBeNull();
  });
});

describe('what the cookies say about a browser with no live session', () => {
  const table: readonly (readonly [string | null, 'open' | 'ended' | 'invalid' | null, string | null])[] = [
    // [session cookie as received, note, reason]
    [null, null, null], // a first visit, or a signed-out browser: nothing to say
    ['', null, null], // an emptied cookie is no cookie
    [null, 'open', 'expired'], // the cookie lapsed; the note remembers a session was opened
    [null, 'ended', 'ended'],
    [null, 'invalid', 'invalid'],
    [UNKNOWN_ID, null, 'invalid'], // a cookie that names no session here
    ['garbage', null, 'invalid'], // present, malformed: names no session either
    [UNKNOWN_ID, 'open', 'invalid'], // the cookie was sent, so it did not lapse
    [UNKNOWN_ID, 'ended', 'ended'], // the server's own record comes first
    [UNKNOWN_ID, 'invalid', 'invalid'],
  ];

  for (const [cookie, note, reason] of table) {
    it(`cookie ${JSON.stringify(cookie)} with note ${String(note)} → ${String(reason)}`, () => {
      expect(guestSessionReason(cookie, note)).toBe(reason);
    });
  }

  it('reads the same answer off a Cookie header, ignoring a note outside the closed list', () => {
    expect(guestSessionReasonFromHeader(null)).toBeNull();
    expect(guestSessionReasonFromHeader(`${SESSION_NOTE_COOKIE}=open`)).toBe('expired');
    expect(guestSessionReasonFromHeader(`${SESSION_NOTE_COOKIE}=boom`)).toBeNull();
    expect(guestSessionReasonFromHeader(`${SESSION_COOKIE}=${UNKNOWN_ID}`)).toBe('invalid');
  });
});

// ================================================== 2. the doors that write the note, end to end

interface Upstream {
  readonly path: string;
  readonly method: string;
}

let seen: Upstream[] = [];
let mintCounter = 0;
let refused: Set<string>;
const ORIGINAL = {
  upstream: process.env.AUDITMANAGER_API_UPSTREAM,
  token: process.env.AUDITMANAGER_API_TOKEN,
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
}

const EPOCH_RAISED = (): Response =>
  json(
    {
      contract_version: '1.43.0',
      correlation_id: 'reason-epoch',
      error_code: 'authentication_required',
      message: 'The credential is not accepted.',
      retryable: false,
    },
    401,
  );

beforeEach(() => {
  jar.cookies.clear();
  forgetEverySession();
  forgetEveryGuestBucket();
  seen = [];
  refused = new Set();
  process.env.AUDITMANAGER_API_UPSTREAM = UPSTREAM;
  process.env.AUDITMANAGER_API_TOKEN = DEPLOYMENT_TOKEN;
  vi.stubGlobal('fetch', async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = new URL(String(input)).pathname;
    const method = init?.method ?? 'GET';
    const authorization = new Headers(init?.headers ?? {}).get('authorization');
    seen.push({ path, method });
    if (method === 'POST' && path === '/auth/token') {
      mintCounter += 1;
      return json({ token: `reason-minted-${mintCounter}`, expires_in: LIFETIME, is_default_credential: false });
    }
    if (authorization !== null && refused.has(authorization.replace(/^Bearer /, ''))) return EPOCH_RAISED();
    if (method === 'GET' && path === '/me') return accountAnswer();
    return json({ items: [], next_cursor: null });
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  jar.cookies.clear();
  forgetEverySession();
  forgetEveryGuestBucket();
  if (ORIGINAL.upstream === undefined) delete process.env.AUDITMANAGER_API_UPSTREAM;
  else process.env.AUDITMANAGER_API_UPSTREAM = ORIGINAL.upstream;
  if (ORIGINAL.token === undefined) delete process.env.AUDITMANAGER_API_TOKEN;
  else process.env.AUDITMANAGER_API_TOKEN = ORIGINAL.token;
});

/** What a browser does with the `Set-Cookie` lines of an answer: keep them, or drop at `Max-Age=0`. */
function browserReceives(response: Response): void {
  for (const line of response.headers.getSetCookie()) {
    const [pair = '', ...attributes] = line.split(';').map((part) => part.trim());
    const at = pair.indexOf('=');
    const name = pair.slice(0, at);
    const value = pair.slice(at + 1);
    const dropped = attributes.includes('Max-Age=0') || value === '';
    if (dropped) jar.cookies.delete(name);
    else jar.cookies.set(name, value);
  }
}

function cookieHeader(): string | undefined {
  const pairs = [...jar.cookies].map(([name, value]) => `${name}=${value}`);
  return pairs.length === 0 ? undefined : pairs.join('; ');
}

function request(path: string, method: string, body?: Record<string, string>): Request {
  const cookie = cookieHeader();
  return new Request(`http://web.test/bff/v1/${path}`, {
    method,
    headers: {
      ...(cookie === undefined ? {} : { cookie }),
      ...(body === undefined ? {} : { 'content-type': 'application/x-www-form-urlencoded' }),
    },
    ...(body === undefined ? {} : { body: new URLSearchParams(body).toString() }),
  });
}

async function door(path: string, method = 'POST', body?: Record<string, string>): Promise<Response> {
  const handler = method === 'GET' ? GET : POST;
  const segments = (path.split('?')[0] ?? path).split('/');
  const response = await handler(request(path, method, body), { params: Promise.resolve({ path: segments }) });
  browserReceives(response);
  return response;
}

async function signIn(): Promise<Response> {
  return door('session', 'POST', { login: 'reviewer@example.test', password: 'a-password' });
}

function mintedToken(): string {
  return `reason-minted-${mintCounter}`;
}

/** Where the guard sends the browser from `/projects`, as the address; `null` when it renders. */
async function guardSends(): Promise<string | null> {
  const screen = screenAt('/projects');
  if (screen === undefined) throw new Error('/projects is not registered');
  try {
    await enforceScreen(screen, {});
    return null;
  } catch (thrown) {
    const digest = (thrown as { digest?: unknown } | null)?.digest;
    if (typeof digest !== 'string' || !digest.startsWith('NEXT_REDIRECT;')) throw thrown;
    return digest.split(';')[2] ?? null;
  }
}

const NEXT = `next=${encodeURIComponent('/projects')}`;

describe('sign-in and sign-out keep the note in step with the session', () => {
  it('sets the session cookie first and the `open` note second, living a week past the session', async () => {
    const response = await signIn();
    expect(response.status).toBe(303);
    const lines = response.headers.getSetCookie();
    expect(lines).toHaveLength(2);
    expect(lines[0]?.startsWith(`${SESSION_COOKIE}=`)).toBe(true);
    expect(lines[1]).toBe(openNoteCookie(LIFETIME, false));
    expect(jar.cookies.get(SESSION_NOTE_COOKIE)).toBe('open');
    expect(openSessionCount()).toBe(1);
  });

  it('replaces an `ended` note with `open` when the person signs in again', async () => {
    jar.cookies.set(SESSION_NOTE_COOKIE, 'ended');
    await signIn();
    expect(jar.cookies.get(SESSION_NOTE_COOKIE)).toBe('open');
  });

  it('removes the session cookie and the note together on an explicit sign-out: no explanation owed', async () => {
    await signIn();
    const out = await door('session/end');
    expect(out.status).toBe(303);
    expect(out.headers.get('location')).toBe('/login');
    const lines = out.headers.getSetCookie();
    expect(lines).toHaveLength(2);
    expect(lines).toContain(clearedNoteCookie(false));
    expect(jar.cookies.size).toBe(0);
    expect(await guardSends()).toBe(`/login?${NEXT}`);
  });
});

describe('ended: the API stopped accepting a credential the register held as live', () => {
  it('answers the API’s own 401, clears the session cookie and writes the `ended` note', async () => {
    await signIn();
    refused.add(mintedToken());
    const response = await door('projects', 'GET');
    expect(response.status).toBe(401);
    const lines = response.headers.getSetCookie();
    expect(lines).toHaveLength(2);
    expect(lines[0]).toContain('Max-Age=0');
    expect(lines[0]?.startsWith(`${SESSION_COOKIE}=;`)).toBe(true);
    expect(lines[1]).toBe(endNoteCookie('ended', false));
    expect(openSessionCount()).toBe(0);
  });

  it('is what the next page shows: guard → /login?next=…&reason=ended, and /login says «Сеанс завершён»', async () => {
    await signIn();
    refused.add(mintedToken());
    await door('projects', 'GET');
    expect(await guardSends()).toBe(`/login?${NEXT}&reason=ended`);
    // A direct visit (the frame’s «Войти» link, a client that assigns the address) says it too.
    const element = await LoginRoute({ searchParams: Promise.resolve({}) });
    expect(element.props.reason).toBe('ended');
    expect(render(element)).toContain('Сеанс завершён — войдите снова.');
  });
});

describe('invalid: the cookie names a session this server does not hold', () => {
  it('answers 401 for an API read, clears the cookie, and writes the `invalid` note', async () => {
    jar.cookies.set(SESSION_COOKIE, UNKNOWN_ID);
    const response = await door('projects', 'GET');
    expect(response.status).toBe(401);
    const lines = response.headers.getSetCookie();
    expect(lines).toHaveLength(2);
    expect(lines[1]).toBe(endNoteCookie('invalid', false));
    expect(seen).toEqual([]);
    expect(await guardSends()).toBe(`/login?${NEXT}&reason=invalid`);
  });

  it('is said by the guard before any write: a stale cookie alone is enough', async () => {
    jar.cookies.set(SESSION_COOKIE, UNKNOWN_ID);
    expect(await guardSends()).toBe(`/login?${NEXT}&reason=invalid`);
  });
});

describe('expired: the session cookie lapsed, and the note remembers a session was opened', () => {
  it('is said once the browser drops the cookie at the end of its Max-Age', async () => {
    await signIn();
    expect(await guardSends()).toBeNull(); // a live session opens the screen
    jar.cookies.delete(SESSION_COOKIE); // what the browser does when Max-Age passes
    forgetEverySession(); // and the register's row has expired with it
    expect(await guardSends()).toBe(`/login?${NEXT}&reason=expired`);
    const element = await LoginRoute({ searchParams: Promise.resolve({}) });
    expect(element.props.reason).toBe('expired');
    expect(render(element)).toContain('Сеанс истёк — войдите снова.');
  });

  it('is not claimed for a browser that never signed in', async () => {
    expect(await guardSends()).toBe(`/login?${NEXT}`);
    const element = await LoginRoute({ searchParams: Promise.resolve({}) });
    expect(element.props.reason).toBeNull();
    expect(render(element)).not.toContain('data-sign-in-reason');
  });
});

describe('a post that needs a session and finds none says why, with `next` first', () => {
  const PASSWORD_DOOR = `session/password?next=${encodeURIComponent('/projects')}`;

  it('first visit: back to sign in as before, no reason', async () => {
    const response = await door(PASSWORD_DOOR);
    expect(response.headers.get('location')).toBe(`/login?${NEXT}`);
  });

  it('unknown cookie: `invalid`, the session cookie cleared and the note written', async () => {
    jar.cookies.set(SESSION_COOKIE, UNKNOWN_ID);
    const response = await door(PASSWORD_DOOR);
    expect(response.headers.get('location')).toBe(`/login?${NEXT}&reason=invalid`);
    expect(response.headers.getSetCookie()).toEqual([
      `${SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0`,
      endNoteCookie('invalid', false),
    ]);
  });

  it('lapsed cookie with the `open` note: `expired`, and the note is left alone', async () => {
    jar.cookies.set(SESSION_NOTE_COOKIE, 'open');
    const response = await door(PASSWORD_DOOR);
    expect(response.headers.get('location')).toBe(`/login?${NEXT}&reason=expired`);
    expect(response.headers.getSetCookie().some((line) => line.startsWith(`${SESSION_NOTE_COOKIE}=`))).toBe(false);
  });
});

describe('the executor-secret door says the same two things', () => {
  const KEY = 'a-key-of-sufficient-length';
  const DOOR = `executor-secret/${CONNECTION}`;
  const WHERE = encodeURIComponent(`/workers?tab=connections&connection=${CONNECTION}`);

  it('a guest: no reason on a first visit, `invalid` for a cookie that names nothing', async () => {
    expect((await door(DOOR, 'POST', { value: KEY })).headers.get('location')).toBe(`/login?next=${WHERE}`);
    jar.cookies.set(SESSION_COOKIE, UNKNOWN_ID);
    expect((await door(DOOR, 'POST', { value: KEY })).headers.get('location')).toBe(
      `/login?next=${WHERE}&reason=invalid`,
    );
  });

  it('a 401 on a live session: `ended`, the session closed, the cookie cleared and the note written', async () => {
    await signIn();
    refused.add(mintedToken());
    const response = await door(DOOR, 'POST', { value: KEY });
    expect(response.status).toBe(303);
    expect(response.headers.get('location')).toBe(
      `/login?next=${encodeURIComponent('/workers?tab=connections')}&reason=ended`,
    );
    expect(response.headers.getSetCookie()).toEqual([
      `${SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0`,
      endNoteCookie('ended', false),
    ]);
    expect(openSessionCount()).toBe(0);
  });
});

// ======================================================= 3. the guard and the route read it back

describe('the guard puts the reason after `next`, and only where the cookies say why', () => {
  it('leaves a live session alone whatever the note says', async () => {
    const id = openSession(
      {
        login: 'проверяющий',
        displayLabel: 'Проверяющая А. Б.',
        initials: 'ПА',
        roles: ['expert'],
        isDefaultCredential: false,
        profileComplete: true,
      },
      'a-credential',
      LIFETIME,
    );
    jar.cookies.set(SESSION_COOKIE, id);
    for (const note of ['open', 'ended', 'invalid', 'boom']) {
      jar.cookies.set(SESSION_NOTE_COOKIE, note);
      expect(await guardSends(), note).toBeNull();
    }
  });

  it('ignores a note outside the closed list: a forged value is no reason', async () => {
    for (const forged of ['boom', 'expired', '<script>', 'OPEN', '']) {
      jar.cookies.clear();
      jar.cookies.set(SESSION_NOTE_COOKIE, forged);
      expect(await guardSends(), JSON.stringify(forged)).toBe(`/login?${NEXT}`);
    }
  });

  it('carries each reason on every non-public screen it guards, `next` untouched', async () => {
    jar.cookies.set(SESSION_NOTE_COOKIE, 'ended');
    for (const address of ['/', '/projects', '/account', '/norms']) {
      const screen = screenAt(address);
      if (screen === undefined) throw new Error(`${address} is not registered`);
      let location: string | null = null;
      try {
        await enforceScreen(screen, {});
      } catch (thrown) {
        location = ((thrown as { digest?: string }).digest ?? '').split(';')[2] ?? null;
      }
      expect(location, address).toBe(`/login?next=${encodeURIComponent(address)}&reason=ended`);
    }
  });
});

describe('/login shows the reason it is given, and only a reason from the closed list', () => {
  const props = async (query: Record<string, string | string[]>) =>
    (await LoginRoute({ searchParams: Promise.resolve(query) })).props;

  it('reads each of the three from the address, beside the next the guard sent', async () => {
    for (const reason of SESSION_END_REASONS) {
      expect(await props({ reason, next: '/projects' })).toEqual({
        login: null,
        refusal: null,
        unknownRefusal: false,
        next: '/projects',
        reason,
      });
    }
  });

  it('ignores a value outside the list and never echoes it into the screen', async () => {
    for (const hostile of ['boom', '<script>alert(1)</script>', 'EXPIRED', '', 'session_expired']) {
      const element = await LoginRoute({ searchParams: Promise.resolve({ reason: hostile }) });
      expect(element.props.reason, JSON.stringify(hostile)).toBeNull();
      const markup = render(element);
      expect(markup).not.toContain('data-sign-in-reason');
      expect(markup).not.toContain('alert(1)');
      expect(markup).not.toContain('Сеанс ');
    }
    expect((await props({ reason: ['x', 'ended'] })).reason).toBeNull();
    expect((await props({ reason: ['ended', 'x'] })).reason).toBe('ended');
  });

  it('prefers the address, falls back to the cookies, and says nothing when neither does', async () => {
    jar.cookies.set(SESSION_NOTE_COOKIE, 'ended');
    expect((await props({ reason: 'expired' })).reason).toBe('expired');
    expect((await props({})).reason).toBe('ended');
    expect((await props({ reason: 'boom' })).reason).toBe('ended'); // the server’s own record, not the query
    jar.cookies.clear();
    expect((await props({})).reason).toBeNull();
  });

  it('lets the last attempt’s refusal take the place of the reason: one message above the form', async () => {
    jar.cookies.set(SESSION_NOTE_COOKIE, 'ended');
    const element = await LoginRoute({ searchParams: Promise.resolve({ refusal: 'credentials', reason: 'expired' }) });
    expect(element.props.reason).toBeNull();
    const markup = render(element);
    expect(markup).toContain('data-sign-in-refusal="credentials"');
    expect(markup).not.toContain('data-sign-in-reason');
  });
});

// ================================================================================ 4. the markup

describe('the sentence stands above the form, and the form is what it was', () => {
  for (const reason of SESSION_END_REASONS) {
    it(`${reason}: the sentence, its machine value, then the form`, () => {
      const markup = render(SignInPage({ reason, next: '/projects?x=1' }));
      const sentence = signInReasonMessage(reason);
      expect(markup).toContain(`data-sign-in-reason="${reason}"`);
      expect(markup).toContain(sentence);
      expect(markup.indexOf(sentence)).toBeGreaterThan(-1);
      expect(markup.indexOf(sentence)).toBeLessThan(markup.indexOf('<form'));
      // `next` still reaches the form, in the action and in the hidden field.
      expect(markup).toContain('name="next" value="/projects?x=1"');
      expect(markup).toContain('action="/bff/v1/session?next=%2Fprojects%3Fx%3D1"');
      // No reason in the form’s own address: the reason is for reading, never for posting back.
      expect(/<form[^>]*action="[^"]*reason/.test(markup)).toBe(false);
    });
  }

  it('says nothing without a reason, and names a reason once', () => {
    expect(render(SignInPage({}))).not.toContain('data-sign-in-reason');
    expect(render(SignInPage({ reason: null }))).not.toContain('data-sign-in-reason');
    expect(render(SignInPage({ reason: 'ended' })).match(/data-sign-in-reason=/g)).toHaveLength(1);
  });

  it('is a status a screen reader announces, and the sentence carries no Latin letter', () => {
    for (const reason of SESSION_END_REASONS) {
      const markup = render(SignInPage({ reason }));
      const element = new RegExp(`<p[^>]*data-sign-in-reason="${reason}"[^>]*>([^<]*)</p>`).exec(markup);
      expect(element, reason).not.toBeNull();
      expect(element?.[0]).toContain('role="status"');
      expect(element?.[1]).toBe(signInReasonMessage(reason));
      expect(element?.[1]).not.toMatch(/[A-Za-z]/);
    }
  });
});
