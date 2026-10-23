/**
 * `EXEC-HTTP-01` — the commands on a connection, read off the network.
 *
 * The hooks are called with `@tanstack/react-query` replaced by a pass-through, so each
 * `mutationFn` runs the real generated client against a recording `fetch`. What is asserted is
 * what a stand would see: the operation, the path, the JSON body, the caller's idempotency key
 * on every send (a repeat reuses it), no automatic retry, and every execution read refreshed
 * after a success. And one thing that must NOT be on the wire from here at all: a key.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

const calls = vi.hoisted(() => ({ invalidations: [] as unknown[] }));

vi.mock('@tanstack/react-query', () => ({
  useMutation: (configuration: unknown) => configuration,
  useQueryClient: () => ({
    invalidateQueries: (...args: unknown[]) => { calls.invalidations.push(args); return Promise.resolve(); },
  }),
}));

import { queryKeys } from '@/shared/api';
import {
  useArchiveExecutorConnection,
  useCreateExecutorConnection,
  useGenerateExecutorSshKey,
  useIssueRunnerToken,
  useRequestExecutorProbe,
  useReviseExecutorConnection,
  useRevokeRunnerToken,
  useSetExecutorRoute,
} from '@/features/manage-executor-connection';

const CONNECTION = 'exc_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const OTHER = 'exc_01J9ZQ8K7NHVXW3T2R5M6P4Q8G';
const KEY = 'ik-one-connection-intent';

type Captured<T, U> = {
  mutationFn: (input: T) => Promise<U>;
  onSuccess: (result: U) => void;
  retry: boolean;
};

let requests: { method: string; path: string; body: string; key: string | null }[] = [];
let answer: { status: number; body: unknown } = { status: 200, body: {} };

beforeEach(() => {
  calls.invalidations.length = 0;
  requests = [];
  answer = { status: 200, body: {} };
  vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', 'http://web.test/bff/v1');
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string, init: RequestInit) => {
      const headers = new Headers(init.headers);
      requests.push({
        method: init.method ?? 'GET',
        path: new URL(input).pathname,
        body: init.body === undefined || init.body === null ? '' : String(init.body),
        key: headers.get('Idempotency-Key'),
      });
      return new Response(JSON.stringify(answer.body), {
        status: answer.status, headers: { 'content-type': 'application/json' },
      });
    }),
  );
});

const SETTINGS = {
  pin_id: 'claude-sonnet-5', gateway_model: 'anthropic/claude-sonnet-5', billing: 'metered' as const,
  allow_client_documents: false, timeout_seconds: 120,
  api_flavour: 'openai_chat' as const, base_url: 'https://openrouter.ai/api/v1', transport: 'direct' as const,
  max_parallel_calls: 1,
};

describe('create then revise: a connection is a name and a kind, its settings are its first revision', () => {
  it('sends the creation and the first revision, each under its own key, and repeats with the same one', async () => {
    answer = { status: 201, body: { connection_id: CONNECTION } };
    const create = useCreateExecutorConnection() as unknown as Captured<
      { kind: string; displayName: string; idempotencyKey: string }, unknown>;
    expect(create.retry).toBe(false);
    await create.mutationFn({ kind: 'http_api', displayName: 'Основной шлюз', idempotencyKey: KEY });
    await create.mutationFn({ kind: 'http_api', displayName: 'Основной шлюз', idempotencyKey: KEY });
    const revise = useReviseExecutorConnection() as unknown as Captured<
      { connectionId: string; body: unknown; idempotencyKey: string }, unknown>;
    expect(revise.retry).toBe(false);
    await revise.mutationFn({ connectionId: CONNECTION, body: SETTINGS, idempotencyKey: 'ik-revision' });
    expect(requests).toEqual([
      { method: 'POST', path: '/bff/v1/executor-connections', body: '{"kind":"http_api","display_name":"Основной шлюз"}', key: KEY },
      { method: 'POST', path: '/bff/v1/executor-connections', body: '{"kind":"http_api","display_name":"Основной шлюз"}', key: KEY },
      { method: 'POST', path: `/bff/v1/executor-connections/${CONNECTION}/revisions`, body: JSON.stringify(SETTINGS), key: 'ik-revision' },
    ]);
  });
});

describe('the other commands', () => {
  it('probe, archive and generate-a-key post to their own address with the caller key', async () => {
    answer = { status: 202, body: {} };
    const probe = useRequestExecutorProbe() as unknown as Captured<{ connectionId: string; idempotencyKey: string }, unknown>;
    const archive = useArchiveExecutorConnection() as unknown as Captured<{ connectionId: string; idempotencyKey: string }, unknown>;
    const generate = useGenerateExecutorSshKey() as unknown as Captured<{ connectionId: string; idempotencyKey: string }, unknown>;
    for (const command of [probe, archive, generate]) expect(command.retry).toBe(false);
    await probe.mutationFn({ connectionId: CONNECTION, idempotencyKey: 'ik-probe' });
    await archive.mutationFn({ connectionId: CONNECTION, idempotencyKey: 'ik-archive' });
    await generate.mutationFn({ connectionId: CONNECTION, idempotencyKey: 'ik-ssh' });
    expect(requests).toEqual([
      { method: 'POST', path: `/bff/v1/executor-connections/${CONNECTION}/probes`, body: '', key: 'ik-probe' },
      { method: 'POST', path: `/bff/v1/executor-connections/${CONNECTION}/archive`, body: '', key: 'ik-archive' },
      { method: 'POST', path: `/bff/v1/executor-connections/${CONNECTION}/ssh-key`, body: '', key: 'ik-ssh' },
    ]);
  });

  it('issues a runner token with its lifetime and revokes one by its id, each under the caller key', async () => {
    const TOKEN = 'ern_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
    answer = { status: 201, body: { token: 'ЗНАЧЕНИЕ', runner_token: { token_id: TOKEN } } };
    const issue = useIssueRunnerToken() as unknown as Captured<
      { connectionId: string; expiresInDays: number; idempotencyKey: string }, { token: string }> & { gcTime: number };
    const revoke = useRevokeRunnerToken() as unknown as Captured<
      { connectionId: string; tokenId: string; idempotencyKey: string }, unknown>;
    expect(issue.retry).toBe(false);
    expect(revoke.retry).toBe(false);
    // The value is shown once and kept by nothing: the mutation is dropped as soon as it settles.
    expect(issue.gcTime).toBe(0);
    const issued = await issue.mutationFn({ connectionId: CONNECTION, expiresInDays: 30, idempotencyKey: 'ik-issue' });
    expect(issued.token).toBe('ЗНАЧЕНИЕ');
    answer = { status: 200, body: {} };
    await revoke.mutationFn({ connectionId: CONNECTION, tokenId: TOKEN, idempotencyKey: 'ik-revoke' });
    expect(requests).toEqual([
      { method: 'POST', path: `/bff/v1/executor-connections/${CONNECTION}/runner-tokens`, body: '{"expires_in_days":30}', key: 'ik-issue' },
      { method: 'POST', path: `/bff/v1/executor-connections/${CONNECTION}/runner-tokens/${TOKEN}/revoke`, body: '', key: 'ik-revoke' },
    ]);
  });

  it('a route names the primary and sends a standby only when one is chosen', async () => {
    const route = useSetExecutorRoute() as unknown as Captured<
      { workKind: string; primary: string; standby: string | null; idempotencyKey: string }, unknown>;
    expect(route.retry).toBe(false);
    await route.mutationFn({ workKind: 'text_analysis', primary: CONNECTION, standby: null, idempotencyKey: 'ik-route-1' });
    await route.mutationFn({ workKind: 'text_analysis', primary: CONNECTION, standby: OTHER, idempotencyKey: 'ik-route-2' });
    expect(requests).toEqual([
      { method: 'PUT', path: '/bff/v1/executor-routes', body: `{"work_kind":"text_analysis","primary_connection_id":"${CONNECTION}"}`, key: 'ik-route-1' },
      { method: 'PUT', path: '/bff/v1/executor-routes', body: `{"work_kind":"text_analysis","primary_connection_id":"${CONNECTION}","standby_connection_id":"${OTHER}"}`, key: 'ik-route-2' },
    ]);
  });

  it('refreshes every execution read after a success, and only those', () => {
    for (const hook of [
      useCreateExecutorConnection, useReviseExecutorConnection, useArchiveExecutorConnection,
      useRequestExecutorProbe, useGenerateExecutorSshKey, useSetExecutorRoute,
      useIssueRunnerToken, useRevokeRunnerToken,
    ]) {
      calls.invalidations.length = 0;
      (hook() as unknown as Captured<unknown, unknown>).onSuccess({});
      expect(calls.invalidations).toEqual([[{ queryKey: queryKeys.execution.all() }]]);
    }
    // The connection and route reads live under that root, so the invalidation reaches them.
    for (const key of [queryKeys.execution.connections(), queryKeys.execution.connection(CONNECTION), queryKeys.execution.routes()]) {
      expect(key.slice(0, 1)).toEqual(queryKeys.execution.all());
    }
  });

  it('has no command that carries a key: none of these hooks sends a secret', async () => {
    answer = { status: 201, body: {} };
    const create = useCreateExecutorConnection() as unknown as Captured<{ kind: string; displayName: string; idempotencyKey: string }, unknown>;
    await create.mutationFn({ kind: 'http_api', displayName: 'x', idempotencyKey: KEY });
    expect(requests.some((request) => /secret|value/.test(request.path + request.body))).toBe(false);
  });
});
