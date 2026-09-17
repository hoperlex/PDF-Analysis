/**
 * The credentialed forward: what it attaches, what it refuses to carry, and what it
 * passes through untouched.
 *
 * Every expected value here is a literal. `OPERATING_CONSTRAINTS.md` §12: a test that
 * computed the expected header list from `FORWARDED_REQUEST_HEADERS` would share its
 * assumption with the module under test and would stay green if that list were emptied.
 */

import { describe, expect, it } from 'vitest';

import type { FetchLike } from '@/shared/api';
import {
  BFF_BASE_PATH,
  ForwardPathError,
  buildUpstreamPath,
  forwardWithCredential,
  mintForwardCorrelationId,
} from '@/shared/api/credentialed-forward';

const UPSTREAM = 'http://api:8000';
const TOKEN = 'test-token-not-a-real-credential';
const TARGET = { upstream: UPSTREAM, token: TOKEN };

interface Seen {
  readonly url: string;
  readonly init: RequestInit;
}

/** A fetch that records the call and answers with what the test supplies. */
function recordingFetch(response: () => Response): { fetch: FetchLike; calls: Seen[] } {
  const calls: Seen[] = [];
  const fetch: FetchLike = (url, init) => {
    calls.push({ url, init });
    return Promise.resolve(response());
  };
  return { fetch, calls };
}

function headersOf(init: RequestInit): Headers {
  return new Headers(init.headers as HeadersInit);
}

const okJson = () =>
  new Response('{"items":[]}', {
    status: 200,
    headers: { 'content-type': 'application/json', 'x-correlation-id': 'cid-upstream' },
  });

describe('the browser calls this app, and this app calls the API with the credential', () => {
  it('serves the forward at a same-origin relative base, so the bundle names no origin', () => {
    expect(BFF_BASE_PATH).toBe('/bff/v1');
  });

  it('attaches the deployment credential as a bearer token', async () => {
    const { fetch, calls } = recordingFetch(okJson);
    await forwardWithCredential(new Request('http://localhost/bff/v1/projects'), ['projects'], TARGET, {
      fetch,
    });
    expect(calls).toHaveLength(1);
    expect(headersOf(calls[0]!.init).get('authorization')).toBe(
      'Bearer test-token-not-a-real-credential',
    );
  });

  it('forwards to the upstream origin at the path the segments name', async () => {
    const { fetch, calls } = recordingFetch(okJson);
    await forwardWithCredential(
      new Request('http://localhost/bff/v1/runs/run_01/findings?limit=50&state=open'),
      ['runs', 'run_01', 'findings'],
      TARGET,
      { fetch },
    );
    expect(calls[0]!.url).toBe('http://api:8000/runs/run_01/findings?limit=50&state=open');
  });

  it('replaces a credential the browser tried to supply, and never merges one', async () => {
    const { fetch, calls } = recordingFetch(okJson);
    await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects', {
        headers: { authorization: 'Bearer forged-by-the-browser' },
      }),
      ['projects'],
      TARGET,
      { fetch },
    );
    const sent = headersOf(calls[0]!.init).get('authorization');
    expect(sent).toBe('Bearer test-token-not-a-real-credential');
    expect(sent).not.toContain('forged-by-the-browser');
  });

  it('carries exactly the four request headers the contract surface uses', async () => {
    const { fetch, calls } = recordingFetch(okJson);
    await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects', {
        method: 'POST',
        body: '{"name":"x"}',
        headers: {
          accept: 'application/json',
          'content-type': 'application/json',
          'idempotency-key': 'idem-123',
          'x-correlation-id': 'cid-from-browser',
          cookie: 'session=secret',
          'x-forwarded-for': '203.0.113.9',
          'user-agent': 'a browser',
        },
      }),
      ['projects'],
      TARGET,
      { fetch },
    );
    const sent = headersOf(calls[0]!.init);
    expect(sent.get('accept')).toBe('application/json');
    expect(sent.get('content-type')).toBe('application/json');
    expect(sent.get('idempotency-key')).toBe('idem-123');
    expect(sent.get('x-correlation-id')).toBe('cid-from-browser');
    // The allowlist half: a cookie, the proxy's own headers and the user agent do not go.
    expect(sent.get('cookie')).toBeNull();
    expect(sent.get('x-forwarded-for')).toBeNull();
    expect(sent.get('user-agent')).toBeNull();
    expect([...sent.keys()].sort()).toEqual([
      'accept',
      'authorization',
      'content-type',
      'idempotency-key',
      'x-correlation-id',
    ]);
  });

  it('returns the upstream status and body bytes verbatim, so a 401 arrives as a 401', async () => {
    const envelope =
      '{"contract_version":"1.0.0-draft.1","correlation_id":"cid-abc",' +
      '"error_code":"authentication_required","message":"No valid authenticated subject was presented.",' +
      '"retryable":false}';
    const { fetch } = recordingFetch(
      () =>
        new Response(envelope, {
          status: 401,
          headers: { 'content-type': 'application/json', 'x-correlation-id': 'cid-abc' },
        }),
    );
    const response = await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects'),
      ['projects'],
      TARGET,
      { fetch },
    );
    expect(response.status).toBe(401);
    expect(await response.text()).toBe(envelope);
    expect(response.headers.get('x-correlation-id')).toBe('cid-abc');
  });

  it('republishes exactly three response headers and drops everything else', async () => {
    const { fetch } = recordingFetch(
      () =>
        new Response('bytes', {
          status: 200,
          headers: {
            'content-type': 'text/csv',
            'content-disposition': 'attachment; filename="run.csv"',
            'x-correlation-id': 'cid-csv',
            'set-cookie': 'upstream=leak',
            server: 'uvicorn',
          },
        }),
    );
    const response = await forwardWithCredential(
      new Request('http://localhost/bff/v1/runs/run_01/export.csv'),
      ['runs', 'run_01', 'export.csv'],
      TARGET,
      { fetch },
    );
    expect(response.headers.get('content-type')).toBe('text/csv');
    expect(response.headers.get('content-disposition')).toBe('attachment; filename="run.csv"');
    expect(response.headers.get('x-correlation-id')).toBe('cid-csv');
    expect(response.headers.get('set-cookie')).toBeNull();
    expect(response.headers.get('server')).toBeNull();
  });

  it('sends a request body on a write and none on a read', async () => {
    const write = recordingFetch(okJson);
    await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects', { method: 'POST', body: '{"name":"x"}' }),
      ['projects'],
      TARGET,
      { fetch: write.fetch },
    );
    expect(write.calls[0]!.init.body).toBeDefined();

    const read = recordingFetch(okJson);
    await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects'),
      ['projects'],
      TARGET,
      { fetch: read.fetch },
    );
    expect(read.calls[0]!.init.body).toBeUndefined();
  });

  it('carries no body on a status that may not have one', async () => {
    const { fetch } = recordingFetch(() => new Response(null, { status: 204 }));
    const response = await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects/p_1', { method: 'DELETE' }),
      ['projects', 'p_1'],
      TARGET,
      { fetch },
    );
    expect(response.status).toBe(204);
    expect(response.body).toBeNull();
  });
});

describe('the forward reaches nothing above the API base', () => {
  it('builds a path from segments, percent-encoding each one', () => {
    expect(buildUpstreamPath(['runs', 'run_01HZ', 'findings'])).toBe('/runs/run_01HZ/findings');
    // A space and a `?` are encoded rather than allowed to end the path or start a query.
    expect(buildUpstreamPath(['projects', 'a b?c'])).toBe('/projects/a%20b%3Fc');
  });

  it('refuses a dot segment, an empty segment and a separator inside a segment', () => {
    expect(() => buildUpstreamPath(['..'])).toThrow(ForwardPathError);
    expect(() => buildUpstreamPath(['runs', '..', '..', 'admin'])).toThrow(ForwardPathError);
    expect(() => buildUpstreamPath(['.'])).toThrow(ForwardPathError);
    expect(() => buildUpstreamPath([''])).toThrow(ForwardPathError);
    expect(() => buildUpstreamPath([])).toThrow(ForwardPathError);
  });

  it('answers a traversal attempt with a contract envelope and never calls the API', async () => {
    const { fetch, calls } = recordingFetch(okJson);
    const response = await forwardWithCredential(
      new Request('http://localhost/bff/v1/..'),
      ['..', '..', 'etc'],
      TARGET,
      { fetch },
    );
    expect(calls).toHaveLength(0);
    expect(response.status).toBe(404);
    const body = (await response.json()) as { error_code: string; retryable: boolean };
    expect(body.error_code).toBe('not_found');
    expect(body.retryable).toBe(false);
  });
});

describe('the forward answers an ErrorEnvelope even when the API never did', () => {
  it('reports an unreachable API as a retryable dependency_unavailable', async () => {
    const fetch: FetchLike = () => Promise.reject(new Error('ECONNREFUSED'));
    const response = await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects', {
        headers: { 'x-correlation-id': 'cid-from-browser' },
      }),
      ['projects'],
      TARGET,
      { fetch },
    );
    expect(response.status).toBe(503);
    const body = (await response.json()) as {
      error_code: string;
      retryable: boolean;
      correlation_id: string;
      contract_version: string;
      message: string;
    };
    expect(body.error_code).toBe('dependency_unavailable');
    // The catalog pins this one retryable, and the envelope is where the client reads it.
    expect(body.retryable).toBe(true);
    expect(body.contract_version).toBe('1.0.0-draft.1');
    expect(body.correlation_id).toBe('cid-from-browser');
    // The credential must not appear in anything the browser can read.
    expect(JSON.stringify(body)).not.toContain(TOKEN);
  });

  it('mints a correlation id the contract pattern accepts when the browser sent none', async () => {
    const minted = mintForwardCorrelationId();
    expect(minted).toMatch(/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/);
    expect(minted.startsWith('web-')).toBe(true);

    const fetch: FetchLike = () => Promise.reject(new Error('down'));
    const response = await forwardWithCredential(
      new Request('http://localhost/bff/v1/projects'),
      ['projects'],
      TARGET,
      { fetch },
    );
    const body = (await response.json()) as { correlation_id: string };
    expect(body.correlation_id).toMatch(/^web-[0-9a-f]{32}$/);
    expect(response.headers.get('x-correlation-id')).toBe(body.correlation_id);
  });
});
