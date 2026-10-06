/**
 * The password change: what crosses each boundary, and what the screen says about it.
 *
 * The same two boundaries the sign-in tests are about, with one difference that is the
 * whole of `R-26`:
 *
 *   **towards the API** — two passwords are sent exactly once, to one address, with the
 *   REVIEWER's credential and never the deployment's. The deployment secret is the key the
 *   API signs with; forwarding it here would be `W37CERT4-3` one operation over.
 *   **towards the browser** — the *replacement* credential the API answers with is not in
 *   the answer, in any header, in any cookie, or anywhere a browser retains. `changePassword`
 *   answers with a live credential because it revokes the caller's own in the act of
 *   succeeding, so this boundary matters more here than at the exchange, not less.
 *
 * And one property neither sign-in test could have: the session row is **replaced**. The old
 * credential is dead the moment the API answers, so a handler that left it in the register
 * would leave a row authorising nothing behind a cookie the browser still sends.
 *
 * Since `W49-BFF-01` both the sign-in and a successful change are followed by `getMe`, so the
 * stub answers `GET /me` from `me` and every other call from the `answers` queue, and the
 * replacement row carries the subject `getMe` describes when asked with the replacement.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { GET, POST } from '@/app/bff/v1/[...path]/route';
import { ChangePasswordPage } from '@/_pages/change-password';
import type { ChangePasswordOutcome } from '@/features/change-password';
import {
  CHANGE_PASSWORD_OUTCOMES,
  CHANGE_PASSWORD_PATH,
  CHANGE_PASSWORD_SUBMIT_PATH,
  changePasswordMessage,
  changePasswordOutcomeUrl,
} from '@/features/change-password';
import { SIGN_IN_PATH } from '@/features/sign-in';
import { forgetEveryGuestBucket } from '@/app/bff/session/guest-throttle';
import { forgetEverySession, openSessionCount, subjectOf } from '@/app/bff/session/store';

import { ACCOUNT_LOGIN, accountAnswer } from './account-fixture';

import { WEB_ROOT } from '../../guards/lib/repo';
import { render } from '../review/fixtures';

const UPSTREAM = 'http://api.test:8000';
const DEPLOYMENT_TOKEN = 'deployment-credential-a1b2';
const MINTED = 'minted-token-for-the-reviewer-c3d4';
const REPLACEMENT = 'the-credential-that-replaces-it-e5f6';
const LOGIN = 'проверяющий';
const PASSWORD = 'пароль-который-не-должен-утечь';
const NEW_PASSWORD = 'новый-пароль-тоже-не-должен-утечь';

const SLICE_FILES = [
  'src/features/change-password/model/exchange.ts',
  'src/features/change-password/ui/change-password-form.tsx',
  'src/features/change-password/index.ts',
  'src/_pages/change-password/ui/change-password-page.tsx',
  'src/_pages/change-password/index.ts',
  'src/app/account/password/page.tsx',
];

interface Seen {
  readonly url: string;
  readonly method: string;
  readonly authorization: string | null;
  readonly body: string;
}

let seen: Seen[] = [];
let answers: (() => Response)[] = [];
/** `getMe`, `GET /me`: asked after the sign-in and after a successful change. */
let me: () => Response;

const ORIGINAL = {
  upstream: process.env.AUDITMANAGER_API_UPSTREAM,
  token: process.env.AUDITMANAGER_API_TOKEN,
};

/**
 * A minted credential, as the contract declares one: all three properties.
 *
 * `is_default_credential` defaults to `false` here because that is what the API answers a
 * *change*: the write that stores the new digest clears the column in the same statement.
 * It is still a parameter, so the sign-in half of this fixture can produce the other state.
 */
function jsonAnswer(token: string, expiresIn = 3600, isDefault = false): Response {
  return new Response(
    JSON.stringify({ token, expires_in: expiresIn, is_default_credential: isDefault }),
    {
      status: 200,
      headers: { 'content-type': 'application/json' },
    },
  );
}

function refusal(status: number): Response {
  return new Response('{}', { status, headers: { 'content-type': 'application/json' } });
}

beforeEach(() => {
  forgetEverySession();
  forgetEveryGuestBucket();
  seen = [];
  answers = [];
  me = () => accountAnswer();
  process.env.AUDITMANAGER_API_UPSTREAM = UPSTREAM;
  process.env.AUDITMANAGER_API_TOKEN = DEPLOYMENT_TOKEN;
  vi.stubGlobal('fetch', async (input: RequestInfo | URL, init?: RequestInit) => {
    const headers = new Headers(init?.headers ?? {});
    const raw = init?.body;
    const method = init?.method ?? 'GET';
    seen.push({
      url: String(input),
      method,
      authorization: headers.get('authorization'),
      body: raw === undefined || raw === null ? '' : new TextDecoder().decode(raw as ArrayBuffer),
    });
    if (method === 'GET' && new URL(String(input)).pathname === '/me') return me();
    const next = answers.shift();
    return next === undefined ? jsonAnswer(MINTED) : next();
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

/** Sign in the way a browser does, and return the cookie it was given. */
async function openASession(): Promise<string> {
  answers = [() => jsonAnswer(MINTED)];
  const response = await POST(
    new Request('http://web.test/bff/v1/session', {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ login: LOGIN, password: PASSWORD }).toString(),
    }),
    { params: Promise.resolve({ path: ['session'] }) },
  );
  seen = [];
  const header = response.headers.get('set-cookie');
  expect(header).not.toBeNull();
  return (header as string).split(';')[0] as string;
}

/** Post the password-change form the way a browser posts it. */
function changePassword(
  cookie: string | undefined,
  fields: Record<string, string> = {
    current_password: PASSWORD,
    new_password: NEW_PASSWORD,
    confirm_new_password: NEW_PASSWORD,
  },
): Promise<Response> {
  return POST(
    new Request(`http://web.test${CHANGE_PASSWORD_SUBMIT_PATH}`, {
      method: 'POST',
      headers: {
        'content-type': 'application/x-www-form-urlencoded',
        ...(cookie === undefined ? {} : { cookie }),
      },
      body: new URLSearchParams(fields).toString(),
    }),
    { params: Promise.resolve({ path: ['session', 'password'] }) },
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

function cookieFrom(response: Response): string {
  const header = response.headers.get('set-cookie');
  expect(header).not.toBeNull();
  return (header as string).split(';')[0] as string;
}

describe('the change happens on the server, and the replacement stops there', () => {
  it('sends both passwords once, to one address, with the reviewer credential', async () => {
    const cookie = await openASession();
    answers = [() => jsonAnswer(REPLACEMENT)];

    const response = await changePassword(cookie);
    expect(response.status).toBe(303);

    // The change, then `getMe` asked with the replacement -- and the passwords only in the first.
    expect(seen).toHaveLength(2);
    expect(seen.filter((entry) => entry.body.includes(PASSWORD))).toHaveLength(1);
    expect(seen[1]?.url).toBe(`${UPSTREAM}/me`);
    expect(seen[1]?.method).toBe('GET');
    expect(seen[1]?.authorization).toBe(`Bearer ${REPLACEMENT}`);
    expect(seen[1]?.body).toBe('');
    const call = seen[0] as Seen;
    // `AUDITMANAGER_API_UPSTREAM` already carries the version prefix in a deployment;
    // the forwarder appends the contract path to whatever it is given, and this test
    // configures a bare origin exactly as `bff-session.test.ts` does for the exchange.
    expect(call.url).toBe(`${UPSTREAM}/auth/password`);
    expect(call.method).toBe('POST');
    // The reviewer's credential, not the deployment's. The deployment secret is the key the
    // API SIGNS with: presenting it would be useless and would leak key material into an
    // `Authorization` header, which is exactly `W37CERT4-3`.
    expect(call.authorization).toBe(`Bearer ${MINTED}`);
    expect(call.authorization).not.toContain(DEPLOYMENT_TOKEN);
    expect(JSON.parse(call.body)).toEqual({
      current_password: PASSWORD,
      new_password: NEW_PASSWORD,
    });
  });

  it('returns neither password nor either credential to the browser', async () => {
    const cookie = await openASession();
    answers = [() => jsonAnswer(REPLACEMENT)];

    const response = await changePassword(cookie);
    const headers = [...response.headers.entries()].map(([k, v]) => `${k}: ${v}`).join('\n');
    const body = await response.text();
    const received = `${headers}\n${body}`;

    expect(received).not.toContain(REPLACEMENT);
    expect(received).not.toContain(MINTED);
    expect(received).not.toContain(PASSWORD);
    expect(received).not.toContain(NEW_PASSWORD);
    expect(received).not.toContain(DEPLOYMENT_TOKEN);
    expect(body).toBe('');
  });

  it('replaces the session: a new number, one row, and the old cookie names nothing', async () => {
    const before = await openASession();
    answers = [() => jsonAnswer(REPLACEMENT)];

    const response = await changePassword(before);
    const after = cookieFrom(response);

    expect(after).not.toBe(before);
    // One row, not two. The old credential is dead the moment the API answered, so a row
    // still holding it would authorise nothing behind a cookie the browser still sends.
    expect(openSessionCount()).toBe(1);

    const stale = await listProjects(before);
    expect(stale.status).toBe(401);
  });

  it('forwards the replacement on the next request, not the credential it replaced', async () => {
    const before = await openASession();
    answers = [() => jsonAnswer(REPLACEMENT)];
    const after = cookieFrom(await changePassword(before));

    seen = [];
    answers = [() => new Response('[]', { status: 200 })];
    await listProjects(after);

    expect(seen).toHaveLength(1);
    expect((seen[0] as Seen).authorization).toBe(`Bearer ${REPLACEMENT}`);
  });

  it('lands on the password screen saying it changed', async () => {
    const cookie = await openASession();
    answers = [() => jsonAnswer(REPLACEMENT)];
    const response = await changePassword(cookie);
    expect(response.headers.get('location')).toBe(changePasswordOutcomeUrl('changed'));
  });
});

describe('every way it can refuse, and none of them changes the session', () => {
  it('sends nothing at all without a session, and points at the sign-in screen', async () => {
    const response = await changePassword(undefined);
    expect(seen).toEqual([]);
    expect(response.status).toBe(303);
    expect(response.headers.get('location')).toBe(SIGN_IN_PATH);
  });

  it('refuses a new password equal to the current one before anything is sent', async () => {
    const cookie = await openASession();
    const response = await changePassword(cookie, {
      current_password: PASSWORD,
      new_password: PASSWORD,
      confirm_new_password: PASSWORD,
    });
    // Nothing went out. The API refuses this independently -- its rule is the one that
    // counts -- and this one means no request carrying two passwords is made for nothing.
    expect(seen).toEqual([]);
    expect(response.headers.get('location')).toBe(changePasswordOutcomeUrl('unchanged'));
    expect(openSessionCount()).toBe(1);
  });

  it('refuses an empty field before anything is sent', async () => {
    const cookie = await openASession();
    const response = await changePassword(cookie, {
      current_password: PASSWORD,
      new_password: '',
      confirm_new_password: '',
    });
    expect(seen).toEqual([]);
    expect(response.headers.get('location')).toBe(changePasswordOutcomeUrl('validation'));
  });

  it("refuses the new password and its confirmation when they disagree, R-48's confirmation", async () => {
    const cookie = await openASession();
    const response = await changePassword(cookie, {
      current_password: PASSWORD,
      new_password: NEW_PASSWORD,
      confirm_new_password: `${NEW_PASSWORD}-typo`,
    });
    // Nothing went out: the mismatch is caught before the request to the API is built, so
    // the API never sees the confirmation field at all.
    expect(seen).toEqual([]);
    expect(response.headers.get('location')).toBe(changePasswordOutcomeUrl('mismatch'));
    expect(response.headers.get('location')).not.toBe(changePasswordOutcomeUrl('unchanged'));
    expect(openSessionCount()).toBe(1);
  });

  it('reports a refused current password, and leaves the session exactly as it was', async () => {
    const cookie = await openASession();
    answers = [() => refusal(401)];

    const response = await changePassword(cookie);
    expect(response.headers.get('location')).toBe(changePasswordOutcomeUrl('credentials'));
    // No cookie instruction: nothing about this browser's session changed.
    expect(response.headers.get('set-cookie')).toBeNull();
    expect(openSessionCount()).toBe(1);

    seen = [];
    answers = [() => new Response('[]', { status: 200 })];
    await listProjects(cookie);
    expect((seen[0] as Seen).authorization).toBe(`Bearer ${MINTED}`);
  });

  it("reports the API's own 422 as the same 'unchanged' the local check reports", async () => {
    const cookie = await openASession();
    answers = [() => refusal(422)];
    const response = await changePassword(cookie);
    expect(response.headers.get('location')).toBe(changePasswordOutcomeUrl('unchanged'));
  });

  it('reports an unexpected status as upstream, and keeps the session', async () => {
    const cookie = await openASession();
    answers = [() => refusal(503)];
    const response = await changePassword(cookie);
    expect(response.headers.get('location')).toBe(changePasswordOutcomeUrl('upstream'));
    expect(openSessionCount()).toBe(1);
  });

  it('reports an answer that is not a credential as upstream', async () => {
    const cookie = await openASession();
    answers = [
      () =>
        new Response(JSON.stringify({ token: 42, expires_in: 'soon' }), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
    ];
    const response = await changePassword(cookie);
    expect(response.headers.get('location')).toBe(changePasswordOutcomeUrl('upstream'));
  });

  it('never forwards the reserved segment upstream, whatever the verb', async () => {
    const response = await GET(
      new Request(`http://web.test${CHANGE_PASSWORD_SUBMIT_PATH}`),
      { params: Promise.resolve({ path: ['session', 'password'] }) },
    );
    expect(seen).toEqual([]);
    expect(response.status).toBe(404);
  });

  it('refuses the contract path itself to a browser, so no credential reaches a page', async () => {
    const response = await POST(
      new Request('http://web.test/bff/v1/auth/password', { method: 'POST' }),
      { params: Promise.resolve({ path: ['auth', 'password'] }) },
    );
    expect(seen).toEqual([]);
    expect(response.status).toBe(404);
  });
});

describe('the screen this seam redirects to can render every outcome it produces', () => {
  it('renders each of the seven, with its machine value on a data attribute', () => {
    for (const outcome of CHANGE_PASSWORD_OUTCOMES) {
      const markup = render(
        createElement(ChangePasswordPage, { login: LOGIN, outcome }),
      );
      expect(markup).toContain(`data-change-password-outcome="${outcome}"`);
      expect(markup).toContain(changePasswordMessage(outcome));
    }
  });

  it('offers all three fields and posts to the address the handler answers', () => {
    const markup = render(createElement(ChangePasswordPage, { login: LOGIN }));
    expect(markup).toContain(`action="${CHANGE_PASSWORD_SUBMIT_PATH}"`);
    expect(markup).toContain('method="post"');
    expect(markup).toContain('name="current_password"');
    expect(markup).toContain('name="new_password"');
    expect(markup).toContain('name="confirm_new_password"');
    // Both `new_password` and `confirm_new_password` carry `new-password`: they are the
    // same secret typed twice, not two different ones, and a password manager should
    // treat them as such. Without it on either, a manager offers to save the OLD password
    // as the new one, which would be this screen teaching a reviewer's own tools to undo it.
    expect(markup).toContain('autoComplete="current-password"');
    expect(markup).toContain('autoComplete="new-password"');
    const inputs = markup.match(/<input[^>]*>/g) ?? [];
    expect(inputs.length).toBe(3);
    // No `value=`: the form is uncontrolled, so the markup never carries what was typed.
    for (const input of inputs) expect(input).not.toContain('value=');
    for (const input of inputs) expect(input).toContain('type="password"');
  });

  it('shows no form at all without a session, because it could only be refused', () => {
    const markup = render(createElement(ChangePasswordPage, {}));
    expect(markup).not.toContain('name="current_password"');
    expect(markup).toContain('data-change-password-session="none"');
    expect(markup).toContain(SIGN_IN_PATH);
  });

  it('says out loud that changing the password revokes what was issued', () => {
    const markup = render(createElement(ChangePasswordPage, { login: LOGIN }));
    // The one sentence a reviewer must read BEFORE pressing the button, not after: this
    // action ends every other session they have open, and a screen that only said so
    // afterwards would be reporting a surprise rather than asking for a decision.
    expect(markup).toContain('отзывает');
  });

  it('is built from files that ship no client JavaScript', () => {
    for (const relative of SLICE_FILES) {
      const source = readFileSync(join(WEB_ROOT, relative), 'utf8');
      const code = source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '').trim();
      expect(code.startsWith("'use client'"), `${relative} declares a client component`).toBe(false);
      expect(code.startsWith('"use client"'), `${relative} declares a client component`).toBe(false);
      for (const forbidden of ['localStorage', 'sessionStorage', 'document.cookie', 'indexedDB']) {
        expect(code.includes(forbidden), `${relative} touches ${forbidden}`).toBe(false);
      }
    }
  });
});

describe('the handler and the screen agree on the vocabulary', () => {
  /**
   * The two copies of these strings are held together here, the way
   * `bff-session.test.ts` holds the sign-in pair together. The route handler spells the
   * screen's address and the outcome parameter itself rather than importing the feature,
   * because importing it would pull a React tree -- and a `'use client'` boundary -- into
   * the module that holds the deployment secret.
   */
  it('every outcome the handler can redirect to is one the screen can render', () => {
    const handler = readFileSync(
      join(WEB_ROOT, 'src/app/bff/v1/[...path]/route.ts'),
      'utf8',
    );
    const produced = [...handler.matchAll(/reportChange\(\s*'([a-z]+)'/g)].map((m) => m[1]);
    expect(produced.length).toBeGreaterThan(0);
    for (const outcome of produced) {
      expect(CHANGE_PASSWORD_OUTCOMES as readonly string[]).toContain(outcome);
    }
  });

  it('the screen address and the parameter the handler writes are the feature s own', () => {
    const handler = readFileSync(
      join(WEB_ROOT, 'src/app/bff/v1/[...path]/route.ts'),
      'utf8',
    );
    expect(handler).toContain(`CHANGE_PASSWORD_SCREEN = '${CHANGE_PASSWORD_PATH}'`);
    expect(handler).toContain(`SESSION_PASSWORD_SEGMENT = 'password'`);
    expect(CHANGE_PASSWORD_SUBMIT_PATH).toBe('/bff/v1/session/password');
  });

  it('can fail: an outcome the screen does not know is not in the closed set', () => {
    expect(CHANGE_PASSWORD_OUTCOMES as readonly string[]).not.toContain('rotated');
  });
});

describe('the outcome sentences are Russian and name no half of the pair', () => {
  function visibleText(markup: string): string[] {
    const out: string[] = [];
    for (const match of markup.matchAll(/>([^<>]+)</g)) {
      const text = (match[1] ?? '').replace(/&#x27;|&quot;|&amp;|&lt;|&gt;/g, ' ').trim();
      if (text.length > 0) out.push(text);
    }
    for (const attribute of ['placeholder', 'title', 'alt', 'aria-label']) {
      for (const match of markup.matchAll(new RegExp(`\\s${attribute}="([^"]*)"`, 'g'))) {
        const text = (match[1] ?? '').trim();
        if (text.length > 0) out.push(text);
      }
    }
    return out;
  }

  function latinIn(markup: string): string[] {
    return [
      ...new Set(visibleText(markup).flatMap((text) => text.match(/[A-Za-z]+/g) ?? [])),
    ].sort();
  }

  it('puts no Latin letter on any shape of this screen', () => {
    const shapes = [
      render(createElement(ChangePasswordPage, {})),
      render(createElement(ChangePasswordPage, { login: LOGIN })),
      ...CHANGE_PASSWORD_OUTCOMES.map((outcome: ChangePasswordOutcome) =>
        render(createElement(ChangePasswordPage, { login: LOGIN, outcome })),
      ),
    ];
    expect(visibleText(shapes[0] as string).length).toBeGreaterThan(3);
    for (const markup of shapes) expect(latinIn(markup)).toEqual([]);
  });

  it('can fail: the same reading finds a Latin label put on the same screen', () => {
    expect(latinIn('<p>Смена пароля</p><button>Change password</button>')).toEqual([
      'Change',
      'password',
    ]);
  });
});

describe('W49: the replacement row carries the subject getMe describes now', () => {
  it('opens the new row with getMe’s answer, read with the replacement credential', async () => {
    me = () => accountAnswer({ is_default_credential: true, login: 'admin', profile_complete: false });
    const before = await openASession();
    expect(subjectOf(before.split('=')[1] as string)?.isDefaultCredential).toBe(true);

    answers = [() => jsonAnswer(REPLACEMENT)];
    me = () => accountAnswer({ is_default_credential: false, roles: ['admin', 'expert'] });
    const after = cookieFrom(await changePassword(before));

    const subject = subjectOf(after.split('=')[1] as string);
    expect(subject).toMatchObject({
      login: ACCOUNT_LOGIN,
      roles: ['admin', 'expert'],
      isDefaultCredential: false,
      profileComplete: true,
    });
  });

  it('ends the session and sends the reviewer to sign in when getMe cannot say who it is', async () => {
    const before = await openASession();
    answers = [() => jsonAnswer(REPLACEMENT)];
    me = () => new Response('{}', { status: 503 });

    const response = await changePassword(before);
    // The password HAS changed: the API committed it. So not `upstream` -- the reviewer signs
    // in again with the new password, and that sign-in reads the subject.
    expect(response.status).toBe(303);
    expect(response.headers.get('location')).toBe(SIGN_IN_PATH);
    expect(response.headers.get('set-cookie')).toContain('Max-Age=0');
    expect(openSessionCount()).toBe(0);
  });
});
