/**
 * The one transport, and the seven rules in it that nothing was reading.
 *
 * `shared/api/transport.ts` is the only `fetch` in `web/`. Two guards defend its
 * *location* — the ESLint boundary rules and the textual scanner — and both were shown to
 * fire. Nothing defended its *behaviour*: the `W12-WEB` sweep deleted the idempotency
 * requirement, the descriptor-driven query string, the path-parameter check, percent
 * encoding, the unrecognized-code branch, the envelope structure check and the abort
 * classification, and the suite stayed green for all seven.
 *
 * Everything below goes through a generated client function, which is what a slice calls,
 * with the fetch injected. Nothing imports `request` directly: the rule being tested is
 * what a caller gets, not what an internal helper does.
 */

import { describe, expect, it } from 'vitest';

import type { FetchLike } from '@/shared/api';
import {
  ApiError,
  ClientUsageError,
  TransportError,
  UnrecognizedApiError,
  appendDecision,
  getRunStatus,
  listProjects,
} from '@/shared/api';

const BASE_URL = 'https://api.test/v1';
const RUN_ID = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const FINDING_UID = 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const OBSERVATION_ID = 'fobs_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';

interface Recorded {
  readonly url: string;
  readonly method: string | undefined;
  readonly headers: Record<string, string>;
}

/** A fetch that records the request and replies with `body` at `status`. */
function recorder(status: number, body: unknown): { fetch: FetchLike; calls: Recorded[] } {
  const calls: Recorded[] = [];
  const fetch: FetchLike = (url, init) => {
    const headers: Record<string, string> = {};
    new Headers(init.headers).forEach((value, key) => {
      headers[key] = value;
    });
    calls.push({ url, method: init.method, headers });
    return Promise.resolve(
      new Response(JSON.stringify(body), {
        status,
        headers: { 'Content-Type': 'application/json', 'X-Correlation-Id': 'corr-transport' },
      }),
    );
  };
  return { fetch, calls };
}

function runStatusBody(): unknown {
  return {
    run_id: RUN_ID,
    project_uid: 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
    version_uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
    provider_mode: 'recorded',
    created_at: '2026-01-01T00:00:00Z',
    state: 'published',
    stages: [],
  };
}

// ---------------------------------------------------------------------------------------
// A write without a key never leaves
// ---------------------------------------------------------------------------------------

describe('a write carries an idempotency key or it is not sent', () => {
  it('refuses before the request leaves when no key is supplied', async () => {
    const { fetch, calls } = recorder(201, {});
    await expect(
      appendDecision(
        {
          path: { finding_uid: FINDING_UID },
          body: { event_type: 'accept', finding_observation_id: OBSERVATION_ID },
        } as Parameters<typeof appendDecision>[0],
        { baseUrl: BASE_URL, fetch },
      ),
    ).rejects.toBeInstanceOf(ClientUsageError);
    // The point is not the throw, it is that nothing was sent. A generated key would be a
    // second command every time the user retried.
    expect(calls).toEqual([]);
  });

  it('refuses an empty key as firmly as a missing one', async () => {
    const { fetch, calls } = recorder(201, {});
    await expect(
      appendDecision(
        {
          path: { finding_uid: FINDING_UID },
          body: { event_type: 'accept', finding_observation_id: OBSERVATION_ID },
          idempotencyKey: '',
        },
        { baseUrl: BASE_URL, fetch },
      ),
    ).rejects.toBeInstanceOf(ClientUsageError);
    expect(calls).toEqual([]);
  });

  it('sends the key the caller minted, in the Idempotency-Key header', async () => {
    const { fetch, calls } = recorder(201, {
      decision_id: 'dec_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
      finding_uid: FINDING_UID,
      finding_observation_id: OBSERVATION_ID,
      event_type: 'accept',
      verdict: 'accepted',
      comment: null,
      author_label: 'local-reviewer',
      recorded_at: '2026-01-01T00:00:00Z',
      current_verdict: 'accepted',
    });
    await appendDecision(
      {
        path: { finding_uid: FINDING_UID },
        body: { event_type: 'accept', finding_observation_id: OBSERVATION_ID },
        idempotencyKey: 'ik_fixed-for-this-test',
      },
      { baseUrl: BASE_URL, fetch },
    );
    expect(calls[0]?.headers['idempotency-key']).toBe('ik_fixed-for-this-test');
  });

  it('sends no key on a read', async () => {
    const { fetch, calls } = recorder(200, runStatusBody());
    await getRunStatus({ path: { run_id: RUN_ID } }, { baseUrl: BASE_URL, fetch });
    expect(calls[0]?.headers['idempotency-key']).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------------------
// The URL is built from the descriptor
// ---------------------------------------------------------------------------------------

describe('the query string carries the declared parameters and nothing else', () => {
  it('sends a declared parameter', async () => {
    const { fetch, calls } = recorder(200, { items: [], next_cursor: null });
    await listProjects({ query: { limit: 25 } }, { baseUrl: BASE_URL, fetch });
    expect(calls[0]?.url).toBe(`${BASE_URL}/projects?limit=25`);
  });

  it('drops a parameter the operation does not declare', async () => {
    // Iterating the caller's object instead of the descriptor is how a filter nobody
    // declared reaches the server, and how a value the caller never meant to send leaks
    // into a URL.
    const { fetch, calls } = recorder(200, { items: [], next_cursor: null });
    await listProjects(
      { query: { limit: 25, api_key: 'not-a-parameter' } } as Parameters<typeof listProjects>[0],
      { baseUrl: BASE_URL, fetch },
    );
    expect(calls[0]?.url).toBe(`${BASE_URL}/projects?limit=25`);
    expect(calls[0]?.url).not.toContain('api_key');
  });

  it('sends no query string at all when nothing is supplied', async () => {
    const { fetch, calls } = recorder(200, { items: [], next_cursor: null });
    await listProjects({}, { baseUrl: BASE_URL, fetch });
    expect(calls[0]?.url).toBe(`${BASE_URL}/projects`);
  });
});

describe('a path parameter is required, and is encoded', () => {
  it('refuses an empty path parameter before the request leaves', async () => {
    const { fetch, calls } = recorder(200, runStatusBody());
    await expect(
      getRunStatus({ path: { run_id: '' } }, { baseUrl: BASE_URL, fetch }),
    ).rejects.toBeInstanceOf(ClientUsageError);
    // Substituting the empty string would produce `GET /runs/`, which is a different
    // operation and would come back as a 404 the user cannot act on.
    expect(calls).toEqual([]);
  });

  it('percent-encodes a value that would otherwise change the path', async () => {
    const { fetch, calls } = recorder(200, runStatusBody());
    await getRunStatus({ path: { run_id: 'run 1/2?x=1' } }, { baseUrl: BASE_URL, fetch });
    expect(calls[0]?.url).toBe(`${BASE_URL}/runs/run%201%2F2%3Fx%3D1`);
  });
});

// ---------------------------------------------------------------------------------------
// Decoding a failure
// ---------------------------------------------------------------------------------------

describe('a failure body becomes exactly one of the three failure kinds', () => {
  it('becomes an ApiError when the envelope carries a catalog code', async () => {
    const { fetch } = recorder(404, {
      error_code: 'not_found',
      message: 'No such run.',
      correlation_id: 'corr-404',
      retryable: false,
    });
    await expect(
      getRunStatus({ path: { run_id: RUN_ID } }, { baseUrl: BASE_URL, fetch }),
    ).rejects.toBeInstanceOf(ApiError);
  });

  it('becomes an UnrecognizedApiError when the code is outside the catalog', async () => {
    // The server is ahead of the client. Treating it as an ApiError would let a slice
    // branch on a code it has never seen and retry something nobody classified.
    const { fetch } = recorder(422, {
      error_code: 'cost_budget_exhausted',
      message: 'Outside this client contract.',
      correlation_id: 'corr-unknown',
      retryable: true,
    });
    await expect(
      getRunStatus({ path: { run_id: RUN_ID } }, { baseUrl: BASE_URL, fetch }),
    ).rejects.toBeInstanceOf(UnrecognizedApiError);
  });

  it('becomes a TransportError when the JSON body is not an envelope', async () => {
    const { fetch } = recorder(500, { detail: 'Internal Server Error' });
    await expect(
      getRunStatus({ path: { run_id: RUN_ID } }, { baseUrl: BASE_URL, fetch }),
    ).rejects.toBeInstanceOf(TransportError);
  });

  it('becomes a TransportError when the body is not JSON at all', async () => {
    const fetch: FetchLike = () =>
      Promise.resolve(
        new Response('<html>502 Bad Gateway</html>', {
          status: 502,
          headers: { 'Content-Type': 'text/html' },
        }),
      );
    await expect(
      getRunStatus({ path: { run_id: RUN_ID } }, { baseUrl: BASE_URL, fetch }),
    ).rejects.toBeInstanceOf(TransportError);
  });
});

describe('a request that never reached the API is classified by why it did not', () => {
  it('is retryable when the network failed', async () => {
    const fetch: FetchLike = () => Promise.reject(new Error('ECONNREFUSED'));
    const failure = await getRunStatus(
      { path: { run_id: RUN_ID } },
      { baseUrl: BASE_URL, fetch },
    ).catch((error: unknown) => error);
    expect(failure).toBeInstanceOf(TransportError);
    expect((failure as TransportError).retryable).toBe(true);
  });

  it('is not retryable when the caller aborted', async () => {
    // An abort is the user changing their mind. Retrying it is the client deciding it
    // knows better, and on a write that is a second command.
    const controller = new AbortController();
    controller.abort();
    const fetch: FetchLike = () => Promise.reject(new Error('aborted'));
    const failure = await getRunStatus(
      { path: { run_id: RUN_ID } },
      { baseUrl: BASE_URL, fetch, signal: controller.signal },
    ).catch((error: unknown) => error);
    expect(failure).toBeInstanceOf(TransportError);
    expect((failure as TransportError).retryable).toBe(false);
    // `W31-RUS`: the sentence is Russian now; the claim it carries is unchanged.
    expect((failure as TransportError).message).toContain('прерван');
  });
});
