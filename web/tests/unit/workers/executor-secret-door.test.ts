/**
 * `EXEC-HTTP-01`: the key of a connection is typed into a server-rendered form and posted
 * to a reserved BFF door, so it is never a JavaScript value.
 *
 * Four properties, each shown failing under a mutation in the report:
 *
 *   1. **the form** is a server component: no client directive, no handler, `type=password`,
 *      `autocomplete=off`, posting natively to the door — and no file under `web/src` calls
 *      `setExecutorSecret`, which is the only other way the key could travel;
 *   2. **towards the API** the key goes once, in a JSON body, to one address, with the
 *      ADMINISTRATOR's credential and an idempotency key, and the purpose is fixed;
 *   3. **towards the browser** the answer is a `303` and nothing more — the key is in no
 *      header, no body and no address, and every outcome is one of a closed eight;
 *   4. **the door refuses** a cross-site post, a post without a session, a malformed address,
 *      a verb that is not `POST` and a key outside the contract's bounds, sending nothing.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { GET, POST } from '@/app/bff/v1/[...path]/route';
import {
  EXECUTOR_SECRET_OUTCOMES,
  SetExecutorSecretForm,
  executorSecretMessage,
  executorSecretScreenUrl,
  executorSecretSubmitPath,
  isExecutorConnectionId,
  isExecutorSecretOutcome,
} from '@/features/set-executor-secret';
import { forgetEveryGuestBucket } from '@/app/bff/session/guest-throttle';
import { forgetEverySession, openSessionCount } from '@/app/bff/session/store';

import { WEB_ROOT, readText, walkFiles } from '../../guards/lib/repo';
import { accountAnswer } from '../session/account-fixture';

const UPSTREAM = 'http://api.test:8000';
const DEPLOYMENT_TOKEN = 'deployment-credential-a1b2';
const MINTED = 'minted-token-for-the-administrator-c3d4';
const CONNECTION = 'exc_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const KEY = 'sk-or-v1-the-key-that-must-not-leak-9f8e7d6c';
const INTENT = 'ik_9b3c2a52-7d1e-4a5e-9d3b-0c2f9a1b2c3d';
const DOOR = 'src/app/bff/v1/[...path]/route.ts';

interface Seen {
  readonly url: string;
  readonly method: string;
  readonly authorization: string | null;
  readonly idempotencyKey: string | null;
  readonly body: string;
}

let seen: Seen[] = [];
let answer: () => Response;

const ORIGINAL = {
  upstream: process.env.AUDITMANAGER_API_UPSTREAM,
  token: process.env.AUDITMANAGER_API_TOKEN,
};

function json(status: number, body: unknown = {}): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
}

function sealed(): Response {
  return json(201, { secret_id: 'exs_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', last4: KEY.slice(-4) });
}

beforeEach(() => {
  forgetEverySession();
  forgetEveryGuestBucket();
  seen = [];
  answer = sealed;
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
      idempotencyKey: headers.get('idempotency-key'),
      body: raw === undefined || raw === null ? '' : new TextDecoder().decode(raw as ArrayBuffer),
    });
    if (method === 'GET' && new URL(String(input)).pathname === '/me') {
      return accountAnswer({ roles: ['admin'] });
    }
    if (method === 'POST' && new URL(String(input)).pathname === '/auth/token') {
      return json(200, { token: MINTED, expires_in: 3600, is_default_credential: false });
    }
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

async function signIn(): Promise<string> {
  const response = await POST(
    new Request('http://web.test/bff/v1/session', {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ login: 'admin@example.test', password: 'пароль-администратора' }).toString(),
    }),
    { params: Promise.resolve({ path: ['session'] }) },
  );
  const header = response.headers.get('set-cookie');
  expect(header).not.toBeNull();
  seen = [];
  return (header as string).split(';')[0] as string;
}

function postKey(
  cookie: string | undefined,
  fields: Record<string, string> = { value: KEY, intent: INTENT },
  extraHeaders: Record<string, string> = {},
  connectionId: string = CONNECTION,
): Promise<Response> {
  return POST(
    new Request(`http://web.test${executorSecretSubmitPath(connectionId)}`, {
      method: 'POST',
      headers: {
        'content-type': 'application/x-www-form-urlencoded',
        ...(cookie === undefined ? {} : { cookie }),
        ...extraHeaders,
      },
      body: new URLSearchParams(fields).toString(),
    }),
    { params: Promise.resolve({ path: ['executor-secret', connectionId] }) },
  );
}

function address(outcome: string): string {
  return `/workers?tab=connections&connection=${CONNECTION}&secret=${outcome}`;
}

describe('the form is a server component that posts natively', () => {
  const FILES = [
    'src/features/set-executor-secret/ui/set-executor-secret-form.tsx',
    'src/features/set-executor-secret/model/exchange.ts',
    'src/features/set-executor-secret/index.ts',
  ];

  it('declares no client component and touches no browser storage', () => {
    for (const relative of FILES) {
      const code = readFileSync(join(WEB_ROOT, relative), 'utf8')
        .replace(/\/\*[\s\S]*?\*\//g, '')
        .replace(/^\s*\/\/.*$/gm, '')
        .trim();
      expect(code.startsWith("'use client'"), `${relative} declares a client component`).toBe(false);
      expect(code.startsWith('"use client"'), `${relative} declares a client component`).toBe(false);
      for (const forbidden of ['localStorage', 'sessionStorage', 'document.cookie', 'indexedDB', 'useState', 'onChange', 'onSubmit']) {
        expect(code.includes(forbidden), `${relative} uses ${forbidden}`).toBe(false);
      }
    }
  });

  it('is a password field, not autofilled, posting to the door of its own connection', () => {
    const markup = renderToStaticMarkup(createElement(SetExecutorSecretForm, { connectionId: CONNECTION }));
    expect(markup).toContain('method="post"');
    expect(markup).toContain(`action="/bff/v1/executor-secret/${CONNECTION}"`);
    const field = (markup.match(/<input[^>]*name="value"[^>]*>/) ?? [''])[0];
    expect(field).toContain('type="password"');
    expect(field).toContain('autoComplete="off"');
    expect(field).not.toContain('value=');
    // One field the person types in, and one hidden idempotency key minted when rendered.
    const inputs = markup.match(/<input[^>]*>/g) ?? [];
    expect(inputs).toHaveLength(2);
    expect(markup).toMatch(/<input[^>]*type="hidden"[^>]*name="intent"[^>]*value="ik_[0-9a-f-]{36}"/);
    expect(markup).toContain('data-executor-secret-form');
  });

  it('mints a fresh idempotency key for each rendering of the page', () => {
    const render = () =>
      renderToStaticMarkup(createElement(SetExecutorSecretForm, { connectionId: CONNECTION }))
        .match(/name="intent"[^>]*value="([^"]+)"/)?.[1];
    const intents = [render(), render()];
    expect(intents[0]).toBeDefined();
    expect(intents[0]).not.toBe(intents[1]);
  });

  it('renders the previous outcome beside its machine value, in Russian', () => {
    for (const outcome of EXECUTOR_SECRET_OUTCOMES) {
      const markup = renderToStaticMarkup(createElement(SetExecutorSecretForm, { connectionId: CONNECTION, outcome }));
      expect(markup).toContain(`data-executor-secret-outcome="${outcome}"`);
      expect(markup).toMatch(/[А-Яа-я]{4}/);
      expect(executorSecretMessage(outcome)).toMatch(/Ключ/);
    }
  });

  /** True when the code (comments removed) names the operation: an import, a call or a reference. */
  function namesTheOperation(source: string): boolean {
    const code = source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
    return /\bsetExecutorSecret\b/.test(code);
  }

  it('is the only way the key travels: no code under web/src names setExecutorSecret', () => {
    const callers = walkFiles(join(WEB_ROOT, 'src'), (path) => /\.(ts|tsx)$/.test(path))
      // The generated client and its barrel are the operation's definition, not a use of it.
      .filter((path) => !path.includes(join('shared', 'api', 'generated')))
      .filter((path) => namesTheOperation(readText(path)));
    expect(callers).toEqual([]);
  });

  it('can fail: the scan sees an import, a call and a comment-free reference', () => {
    expect(namesTheOperation("import { setExecutorSecret } from '@/shared/api';")).toBe(true);
    expect(namesTheOperation('void setExecutorSecret({ body: { value } });')).toBe(true);
    expect(namesTheOperation('// setExecutorSecret is not called here\n/* setExecutorSecret */')).toBe(false);
  });
});

describe('towards the API: the key goes once, with the administrator, and nothing else', () => {
  it('sends the key in a JSON body to the secret address of its connection', async () => {
    const cookie = await signIn();
    const response = await postKey(cookie);
    expect(response.status).toBe(303);
    expect(seen).toHaveLength(1);
    const call = seen[0] as Seen;
    expect(call.url).toBe(`${UPSTREAM}/executor-connections/${CONNECTION}/secrets`);
    expect(call.method).toBe('POST');
    expect(call.authorization).toBe(`Bearer ${MINTED}`);
    expect(call.authorization).not.toContain(DEPLOYMENT_TOKEN);
    expect(call.idempotencyKey).toBe(INTENT);
    expect(JSON.parse(call.body)).toEqual({ purpose: 'api_key', value: KEY });
  });

  it('fixes the purpose: a posted purpose is not forwarded', async () => {
    const cookie = await signIn();
    await postKey(cookie, { value: KEY, intent: INTENT, purpose: 'ssh_private_key' });
    expect(JSON.parse((seen[0] as Seen).body)).toEqual({ purpose: 'api_key', value: KEY });
  });

  it('does not trim the key: a pasted space is part of it', async () => {
    const cookie = await signIn();
    await postKey(cookie, { value: `  ${KEY} `, intent: INTENT });
    expect(JSON.parse((seen[0] as Seen).body).value).toBe(`  ${KEY} `);
  });

  it('mints an idempotency key when the post carries none the contract accepts', async () => {
    const cookie = await signIn();
    await postKey(cookie, { value: KEY, intent: 'not a key!' });
    expect((seen[0] as Seen).idempotencyKey).toMatch(/^ik_[0-9a-f-]{36}$/);
    await postKey(cookie, { value: KEY });
    expect((seen[1] as Seen).idempotencyKey).toMatch(/^ik_[0-9a-f-]{36}$/);
  });
});

describe('towards the browser: a redirect and a closed word', () => {
  it('answers 303 to the screen and returns neither the key nor its tail nor the token', async () => {
    const cookie = await signIn();
    const response = await postKey(cookie);
    expect(response.status).toBe(303);
    expect(response.headers.get('location')).toBe(address('saved'));
    const received = `${[...response.headers.entries()].map(([k, v]) => `${k}: ${v}`).join('\n')}\n${await response.text()}`;
    expect(received).not.toContain(KEY);
    expect(received).not.toContain(KEY.slice(-4));
    expect(received).not.toContain(MINTED);
    expect(received).not.toContain(DEPLOYMENT_TOKEN);
    expect(response.headers.get('set-cookie')).toBeNull();
  });

  const CASES: ReadonlyArray<readonly [number, string]> = [
    [201, 'saved'],
    [403, 'forbidden'],
    [404, 'not_found'],
    [409, 'conflict'],
    [422, 'validation'],
    [503, 'unavailable'],
    [500, 'upstream'],
    [418, 'upstream'],
  ];
  for (const [status, outcome] of CASES) {
    it(`names ${status} as «${outcome}» and keeps the session`, async () => {
      const cookie = await signIn();
      answer = () => json(status);
      const response = await postKey(cookie);
      expect(response.headers.get('location')).toBe(address(outcome));
      expect(openSessionCount()).toBe(1);
    });
  }

  it('ends the session on a 401 and sends the person to sign in', async () => {
    const cookie = await signIn();
    answer = () => json(401);
    const response = await postKey(cookie);
    expect(response.status).toBe(303);
    expect(response.headers.get('location')).toContain('/login');
    expect(openSessionCount()).toBe(0);
    expect(response.headers.get('set-cookie') ?? '').toContain('Max-Age=0');
  });

  it('says an unconfigured web tier in its own word, sending nothing', async () => {
    const cookie = await signIn();
    delete process.env.AUDITMANAGER_API_UPSTREAM;
    seen = [];
    const response = await postKey(cookie);
    expect(seen).toEqual([]);
    expect(response.headers.get('location')).toBe(address('unconfigured'));
  });
});

describe('the door refuses, and sends nothing', () => {
  it('refuses a post another site drove, before the session is read', async () => {
    const cookie = await signIn();
    for (const headers of [
      { 'sec-fetch-site': 'cross-site' },
      { origin: 'https://evil.example' },
      { origin: 'null' },
    ]) {
      const response = await postKey(cookie, undefined, headers);
      expect(response.headers.get('location')).toBe(address('validation'));
    }
    expect(seen).toEqual([]);
  });

  it('accepts the same origin, and a post that says nothing about its origin', async () => {
    const cookie = await signIn();
    const same = await postKey(cookie, undefined, { origin: 'http://web.test', 'sec-fetch-site': 'same-origin', host: 'web.test' });
    expect(same.headers.get('location')).toBe(address('saved'));
    const silent = await postKey(cookie);
    expect(silent.headers.get('location')).toBe(address('saved'));
  });

  it('sends a guest to sign in, with nothing forwarded and the key unseen', async () => {
    const response = await postKey(undefined);
    expect(seen).toEqual([]);
    expect(response.status).toBe(303);
    const location = response.headers.get('location') ?? '';
    expect(location).toContain('/login');
    expect(location).not.toContain(KEY);
  });

  it('refuses a key outside the contract bounds before anything is sent', async () => {
    const cookie = await signIn();
    for (const value of ['', 'short', 'x'.repeat(8193)]) {
      const response = await postKey(cookie, { value, intent: INTENT });
      expect(response.headers.get('location')).toBe(address('validation'));
    }
    const missing = await postKey(cookie, { intent: INTENT });
    expect(missing.headers.get('location')).toBe(address('validation'));
    expect(seen).toEqual([]);
  });

  it('accepts a key at each bound', async () => {
    const cookie = await signIn();
    for (const value of ['12345678', 'y'.repeat(8192)]) {
      const response = await postKey(cookie, { value, intent: INTENT });
      expect(response.headers.get('location')).toBe(address('saved'));
    }
  });

  it('answers not_found to an address that is not a connection, and to any other verb', async () => {
    const cookie = await signIn();
    for (const bad of ['exc_short', 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', 'exc_01J9ZQ8K7NHVXW3T2R5M6P4Q8I', '..%2F..']) {
      const response = await postKey(cookie, undefined, {}, bad);
      expect(response.status).toBe(404);
    }
    const get = await GET(
      new Request(`http://web.test/bff/v1/executor-secret/${CONNECTION}`, { headers: { cookie } }),
      { params: Promise.resolve({ path: ['executor-secret', CONNECTION] }) },
    );
    expect(get.status).toBe(404);
    const bare = await POST(
      new Request('http://web.test/bff/v1/executor-secret', { method: 'POST', headers: { cookie } }),
      { params: Promise.resolve({ path: ['executor-secret'] }) },
    );
    expect(bare.status).toBe(404);
    expect(seen).toEqual([]);
  });
});

describe('the door and the feature agree on the vocabulary', () => {
  const handler = readFileSync(join(WEB_ROOT, DOOR), 'utf8');

  /** The string literals of `type <name> = ...;` in `source`, in order. */
  function unionMembers(name: string): string[] {
    const declaration = handler.match(new RegExp(`\\btype ${name} =([^;]+);`));
    if (declaration === null) throw new Error(`no \`type ${name}\` in the handler`);
    return [...(declaration[1] ?? '').matchAll(/'([a-z_]+)'/g)].map((match) => match[1] as string);
  }

  it('declares exactly the eight outcomes the form can render', () => {
    expect(unionMembers('ExecutorSecretOutcome')).toEqual([...EXECUTOR_SECRET_OUTCOMES]);
  });

  it('redirects only with declared values, and with each of them', () => {
    const produced = [...handler.matchAll(/reportSecret\(\s*\w+\s*,\s*'([a-z_]+)'/g)].map((match) => match[1] as string);
    expect(produced.length).toBeGreaterThan(0);
    for (const value of produced) expect(EXECUTOR_SECRET_OUTCOMES as readonly string[]).toContain(value);
    expect(new Set(produced)).toEqual(new Set(EXECUTOR_SECRET_OUTCOMES));
  });

  it('spells the segment, the screen and the parameters the feature spells', () => {
    expect(handler).toContain("EXECUTOR_SECRET_SEGMENT = 'executor-secret'");
    expect(handler).toContain("WORKERS_SCREEN = '/workers'");
    expect(handler).toContain("EXECUTOR_SECRET_CONNECTION_PARAM = 'connection'");
    expect(handler).toContain("EXECUTOR_SECRET_OUTCOME_PARAM = 'secret'");
    expect(handler).toContain("EXECUTOR_SECRET_VALUE_FIELD = 'value'");
    expect(handler).toContain("EXECUTOR_SECRET_INTENT_FIELD = 'intent'");
    expect(executorSecretSubmitPath(CONNECTION)).toBe(`/bff/v1/executor-secret/${CONNECTION}`);
    expect(executorSecretScreenUrl(CONNECTION)).toBe(`/workers?tab=connections&connection=${CONNECTION}`);
  });

  it('holds the contract bounds of the key and the pattern of a connection', () => {
    expect(handler).toContain('EXECUTOR_SECRET_MIN = 8');
    expect(handler).toContain('EXECUTOR_SECRET_MAX = 8192');
    expect(isExecutorConnectionId(CONNECTION)).toBe(true);
    expect(isExecutorConnectionId('exc_01J9ZQ8K7NHVXW3T2R5M6P4Q8I')).toBe(false);
    expect(isExecutorSecretOutcome('saved')).toBe(true);
    expect(isExecutorSecretOutcome('rotated')).toBe(false);
  });

  it('can fail: a value the handler gained alone is named', () => {
    const doctored = handler.replace("| 'upstream';", "| 'upstream' | 'locked';");
    const declaration = doctored.match(/\btype ExecutorSecretOutcome =([^;]+);/);
    const members = [...(declaration?.[1] ?? '').matchAll(/'([a-z_]+)'/g)].map((match) => match[1]);
    expect(members).not.toEqual([...EXECUTOR_SECRET_OUTCOMES]);
  });
});
