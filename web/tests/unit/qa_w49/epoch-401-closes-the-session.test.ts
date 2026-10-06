/**
 * `W49-QA-01`, item 4 (BFF half) — a credential refused after a role removal closes the row.
 *
 * `W49-PLAN.md` §3.5: "Upstream 401 with a held credential (epoch bumped: role change, archive,
 * reset) closes the row and clears the cookie, then answers **the 401 envelope**, exactly as
 * `staleSession` does today — not a redirect". The API half (the role removal really does make
 * the old credential answer 401) is `tests/integration/api/qa_w49/test_qa_w49_role_removal_revokes.py`.
 *
 * Written from the plan, not from the lane's tests: the real route handler, real `Request`
 * objects, and an upstream stubbed by address **and by credential**, so two people can be
 * signed in at once and only one of them can lose their role. Asserted: the API's envelope
 * reaches the browser byte for byte; the cookie is cleared in that answer; exactly the
 * affected row is gone and the other person's is not; the dead cookie sends nothing upstream
 * afterwards; and after signing in again the subject carries the reduced role set, and a
 * `403` on what was lost does not close the new session.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { DELETE, GET, PATCH, POST } from '@/app/bff/v1/[...path]/route';
import { forgetEveryGuestBucket } from '@/app/bff/session/guest-throttle';
import {
  credentialOf,
  forgetEverySession,
  openSessionCount,
  subjectOf,
} from '@/app/bff/session/store';

const UPSTREAM = 'http://api.qa49:8000';
const DEPLOYMENT_TOKEN = 'qa49-deployment-signing-input';

interface Seen {
  readonly path: string;
  readonly method: string;
  readonly authorization: string | null;
}

let seen: Seen[] = [];
/** Which minted credential belongs to which login, and which credentials the API now refuses. */
let mintedFor: Map<string, string>;
let refused: Set<string>;
let rolesOf: Map<string, string[]>;
let mintCounter = 0;

const EPOCH_ENVELOPE = JSON.stringify({
  contract_version: '1.0.0-draft.1',
  correlation_id: 'qa49-api-epoch-raised',
  error_code: 'authentication_required',
  message: 'The credential is not accepted.',
  retryable: false,
});

function json(body: unknown, status = 200, extra: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json', ...extra },
  });
}

function loginOf(credential: string | null): string | null {
  if (credential === null) return null;
  for (const [login, token] of mintedFor) if (`Bearer ${token}` === credential) return login;
  return null;
}

function respond(path: string, method: string, authorization: string | null, body: string): Response {
  if (method === 'POST' && path === '/auth/token') {
    const { login } = JSON.parse(body) as { login: string };
    mintCounter += 1;
    const token = `qa49-minted-${mintCounter}`;
    mintedFor.set(login, token);
    return json({ token, expires_in: 3600, is_default_credential: false });
  }
  if (authorization !== null && refused.has(authorization.replace(/^Bearer /, ''))) {
    return new Response(EPOCH_ENVELOPE, {
      status: 401,
      headers: { 'content-type': 'application/json', 'x-correlation-id': 'qa49-api-epoch-raised' },
    });
  }
  const login = loginOf(authorization);
  if (method === 'GET' && path === '/me' && login !== null) {
    return json({
      user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
      login,
      display_label: 'Проверкина А. Б.',
      last_name: 'Проверкина',
      first_name: 'Анна',
      middle_name: 'Борисовна',
      roles: rolesOf.get(login) ?? [],
      is_default_credential: false,
      profile_complete: true,
      archived_at: null,
    });
  }
  if (path.startsWith('/users') && login !== null && !(rolesOf.get(login) ?? []).includes('admin')) {
    return json(
      {
        contract_version: '1.0.0-draft.1',
        correlation_id: 'qa49-api-403',
        error_code: 'permission_denied',
        message: 'Not permitted.',
        retryable: false,
        details: { required_capability: 'role:admin' },
      },
      403,
    );
  }
  return json({ items: [], next_cursor: null });
}

const ORIGINAL = {
  upstream: process.env.AUDITMANAGER_API_UPSTREAM,
  token: process.env.AUDITMANAGER_API_TOKEN,
};

beforeEach(() => {
  forgetEverySession();
  forgetEveryGuestBucket();
  seen = [];
  mintedFor = new Map();
  refused = new Set();
  rolesOf = new Map([
    ['admin.one@qa.invalid', ['admin', 'expert']],
    ['admin.two@qa.invalid', ['admin', 'expert']],
  ]);
  process.env.AUDITMANAGER_API_UPSTREAM = UPSTREAM;
  process.env.AUDITMANAGER_API_TOKEN = DEPLOYMENT_TOKEN;
  vi.stubGlobal('fetch', async (input: RequestInfo | URL, init?: RequestInit) => {
    const headers = new Headers(init?.headers ?? {});
    const raw = init?.body;
    const method = init?.method ?? 'GET';
    const path = new URL(String(input)).pathname;
    const authorization = headers.get('authorization');
    seen.push({ path, method, authorization });
    const body =
      raw === undefined || raw === null
        ? ''
        : typeof raw === 'string'
          ? raw
          : new TextDecoder().decode(raw as ArrayBuffer);
    return respond(path, method, authorization, body);
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

async function signIn(login: string): Promise<string> {
  const response = await POST(
    new Request('http://web.qa49/bff/v1/session', {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ login, password: 'qa49-any-password' }).toString(),
    }),
    { params: Promise.resolve({ path: ['session'] }) },
  );
  expect(response.status).toBe(303);
  const header = response.headers.get('set-cookie');
  expect(header, `a session for ${login}`).not.toBeNull();
  return (header as string).split(';')[0] as string;
}

function idOf(cookie: string): string {
  return cookie.split('=')[1] as string;
}

type Handler = typeof GET;

const OPERATIONS: ReadonlyArray<{
  readonly name: string;
  readonly handler: Handler;
  readonly method: string;
  readonly path: string[];
  readonly body?: string;
}> = [
  { name: 'listUsers', handler: GET, method: 'GET', path: ['users'] },
  {
    name: 'approveRegistration',
    handler: POST,
    method: 'POST',
    path: ['registrations', 'reg_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', 'approve'],
    body: '{"roles":["expert"]}',
  },
  {
    name: 'updateUser',
    handler: PATCH,
    method: 'PATCH',
    path: ['users', 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8C'],
    body: '{"roles":["expert"]}',
  },
  { name: 'purgeUser', handler: DELETE, method: 'DELETE', path: ['users', 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8C'] },
  {
    name: 'updateMyProfile',
    handler: PATCH,
    method: 'PATCH',
    path: ['me'],
    body: '{"last_name":"Проверкина","first_name":"Анна"}',
  },
];

function call(
  operation: (typeof OPERATIONS)[number],
  cookie: string,
): Promise<Response> {
  const headers: Record<string, string> = { cookie };
  if (operation.body !== undefined) headers['content-type'] = 'application/json';
  if (operation.method === 'POST') headers['idempotency-key'] = 'qa49-key';
  return operation.handler(
    new Request(`http://web.qa49/bff/v1/${operation.path.join('/')}`, {
      method: operation.method,
      headers,
      ...(operation.body === undefined ? {} : { body: operation.body }),
    }),
    { params: Promise.resolve({ path: operation.path }) },
  );
}

describe('W49-QA-01 item 4: an upstream 401 on a held credential ends exactly that session', () => {
  it.each(OPERATIONS.map((operation) => [operation.name, operation] as const))(
    '%s: the envelope verbatim, the cookie cleared, only this row closed',
    async (_name, operation) => {
      const mine = await signIn('admin.one@qa.invalid');
      const theirs = await signIn('admin.two@qa.invalid');
      expect(openSessionCount()).toBe(2);
      const theirCredential = credentialOf(idOf(theirs));
      expect(theirCredential).not.toBeNull();

      // An administrator removed `admin` from the first account: its epoch moved, and the
      // API refuses every credential it held.
      refused.add(mintedFor.get('admin.one@qa.invalid') as string);
      rolesOf.set('admin.one@qa.invalid', ['expert']);
      seen = [];

      const response = await call(operation, mine);
      expect(response.status).toBe(401);
      expect(response.headers.get('location')).toBeNull();
      expect(await response.text()).toBe(EPOCH_ENVELOPE);
      expect(response.headers.get('x-correlation-id')).toBe('qa49-api-epoch-raised');
      const cleared = response.headers.get('set-cookie');
      expect(cleared).not.toBeNull();
      expect(cleared).toContain('Max-Age=0');
      // Exactly one upstream call: the operation itself. A `PATCH /me` that was refused is
      // not followed by a subject refresh.
      expect(seen.map((entry) => `${entry.method} ${entry.path}`)).toEqual([
        `${operation.method} /${operation.path.join('/')}`,
      ]);

      expect(credentialOf(idOf(mine))).toBeNull();
      expect(subjectOf(idOf(mine))).toBeNull();
      expect(openSessionCount()).toBe(1);
      expect(credentialOf(idOf(theirs))).toBe(theirCredential);

      // The dead cookie opens nothing any more: answered here, nothing goes upstream.
      seen = [];
      const after = await call(OPERATIONS[0] as (typeof OPERATIONS)[number], mine);
      expect(after.status).toBe(401);
      expect(seen).toEqual([]);
    },
  );

  it('after signing in again the subject has the reduced role set, and a 403 keeps the session', async () => {
    const first = await signIn('admin.one@qa.invalid');
    expect(subjectOf(idOf(first))?.roles).toEqual(['admin', 'expert']);
    refused.add(mintedFor.get('admin.one@qa.invalid') as string);
    rolesOf.set('admin.one@qa.invalid', ['expert']);
    expect((await call(OPERATIONS[0] as (typeof OPERATIONS)[number], first)).status).toBe(401);

    const second = await signIn('admin.one@qa.invalid');
    expect(subjectOf(idOf(second))?.roles).toEqual(['expert']);
    const lost = await call(OPERATIONS[0] as (typeof OPERATIONS)[number], second);
    expect(lost.status).toBe(403);
    expect(lost.headers.get('set-cookie')).toBeNull();
    expect(credentialOf(idOf(second))).not.toBeNull();
    expect(openSessionCount()).toBe(1);
  });
});
