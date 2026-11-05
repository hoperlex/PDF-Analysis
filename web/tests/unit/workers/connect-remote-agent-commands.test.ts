/**
 * `EXEC2-WEB-WIZARD-01` — the commands behind the wizard, read off the network: the enrollment, the
 * install over SSH, the host-key confirmation, the integration mark, and the hook that creates a
 * connection once and reuses it; and the two bounded re-reads.
 *
 * `@tanstack/react-query` is replaced by a pass-through that also runs `mutationFn`, and `useRef` by a
 * plain cell, so a hook is called outside a render and its `mutationFn` runs the real generated client
 * against a recording `fetch`. What is asserted is what a stand would see: the operation, the path, the
 * JSON body, the caller's idempotency key, no automatic retry, no copy of a shown secret kept by the
 * mutation, and every execution read refreshed after a success. Written under `R-149d`: not run in
 * EXEC-2.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type * as ReactModule from 'react';

const calls = vi.hoisted(() => ({ invalidations: [] as unknown[] }));

vi.mock('@tanstack/react-query', () => ({
  useMutation: (configuration: {
    mutationFn: (variables: unknown) => Promise<unknown>;
    onSuccess?: (data: unknown) => void;
  }) => ({
    ...configuration,
    isPending: false,
    reset: () => undefined,
    mutateAsync: async (variables: unknown) => {
      const data = await configuration.mutationFn(variables);
      configuration.onSuccess?.(data);
      return data;
    },
  }),
  useQuery: (options: unknown) => options,
  useQueryClient: () => ({
    invalidateQueries: (...args: unknown[]) => { calls.invalidations.push(args); return Promise.resolve(); },
  }),
}));

vi.mock('react', async (importOriginal) => {
  const actual = await importOriginal<typeof ReactModule>();
  return { ...actual, useRef: <T,>(initial: T) => ({ current: initial }) };
});

import { CONTRACT_VERSION, queryKeys } from '@/shared/api';
import { AGENT_INSTALL_POLL_MS, AGENT_STATUS_POLL_MS } from '@/shared/config';
import {
  agentInstallQueryKey,
  agentRevisionRequest,
  installIsMoving,
  openRouterRevisionRequest,
  readInstall,
  useAgentInstall,
  useAgentStatusPoll,
  useEnsureConnection,
} from '@/features/connect-remote-agent';
import {
  useConfirmExecutorAgentInstallHostKey,
  useCreateExecutorAgentInstall,
  useIssueExecutorEnrollment,
  useSetExecutorIntegrationAuthorisation,
} from '@/features/manage-executor-connection';

import { connectionId } from './executor-fixtures';
import { NOW, agentCase, agentToken, install, later, MINUTE } from './connect-remote-agent-fixtures';

const CONNECTION = connectionId(63);
const INSTALL = 'exai_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';

type Captured<T, U> = {
  mutationFn: (input: T) => Promise<U>;
  onSuccess: (result: U) => void;
  retry: boolean;
  gcTime?: number;
};

interface Seen { method: string; path: string; body: string; key: string | null }

let requests: Seen[] = [];
let answers: { status: number; body: unknown }[] = [];
let fallback: { status: number; body: unknown } = { status: 200, body: {} };

beforeEach(() => {
  calls.invalidations.length = 0;
  requests = [];
  answers = [];
  fallback = { status: 200, body: {} };
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
      const next = answers.shift() ?? fallback;
      return new Response(JSON.stringify(next.body), { status: next.status, headers: { 'content-type': 'application/json' } });
    }),
  );
});

afterEach(() => {
  vi.useRealTimers();
});

describe('«Новая команда»: a command is issued, shown once and kept by nothing', () => {
  it('posts to the connection’s enrollments under the caller’s key, with no body, and is never retried or kept', async () => {
    fallback = { status: 201, body: { command: 'команда', secret: 'секрет', package_version: '1.2.3', package_sha256: 'x', enrollment: { enrollment_id: 'exen_1' } } };
    const issue = useIssueExecutorEnrollment() as unknown as Captured<{ connectionId: string; idempotencyKey: string }, { command: string }>;
    expect(issue.retry).toBe(false);
    // The secret is in the answer and the mutation is dropped as soon as it settles.
    expect(issue.gcTime).toBe(0);
    const first = await issue.mutationFn({ connectionId: CONNECTION, idempotencyKey: 'ik-one' });
    expect(first.command).toBe('команда');
    expect(requests).toEqual([
      { method: 'POST', path: `/bff/v1/executor-connections/${CONNECTION}/enrollments`, body: '', key: 'ik-one' },
    ]);
  });

  it('is a new intent every time: two presses carry two keys, never the same key twice', async () => {
    fallback = { status: 201, body: { command: 'команда' } };
    const issue = useIssueExecutorEnrollment() as unknown as Captured<{ connectionId: string; idempotencyKey: string }, unknown>;
    await issue.mutationFn({ connectionId: CONNECTION, idempotencyKey: 'ik-one' });
    await issue.mutationFn({ connectionId: CONNECTION, idempotencyKey: 'ik-two' });
    expect(requests.map((request) => request.key)).toEqual(['ik-one', 'ik-two']);
  });

  it('refreshes every execution read after a success, so the new grant appears in the lifecycle', () => {
    for (const hook of [
      useIssueExecutorEnrollment, useCreateExecutorAgentInstall, useConfirmExecutorAgentInstallHostKey,
      useSetExecutorIntegrationAuthorisation,
    ]) {
      calls.invalidations.length = 0;
      (hook() as unknown as Captured<unknown, unknown>).onSuccess({});
      expect(calls.invalidations).toEqual([[{ queryKey: queryKeys.execution.all() }]]);
    }
  });
});

describe('path A: the install, its host key, and the mark', () => {
  it('starts an install with host, port, user and the access; a generated key carries no private key', async () => {
    fallback = { status: 201, body: { install_id: INSTALL } };
    const create = useCreateExecutorAgentInstall() as unknown as Captured<
      { connectionId: string; body: unknown; idempotencyKey: string }, unknown>;
    expect(create.retry).toBe(false);
    await create.mutationFn({
      connectionId: CONNECTION, idempotencyKey: 'ik-install',
      body: { ssh_host: 'host.example', ssh_port: 22, ssh_user: 'installer', access: 'generated_key' },
    });
    expect(requests).toEqual([{
      method: 'POST', path: `/bff/v1/executor-connections/${CONNECTION}/agent-installs`,
      body: '{"ssh_host":"host.example","ssh_port":22,"ssh_user":"installer","access":"generated_key"}', key: 'ik-install',
    }]);
  });

  it('carries no private key from the wizard: the body it builds is host, port, user and the generated-key access', async () => {
    fallback = { status: 201, body: { install_id: INSTALL } };
    const create = useCreateExecutorAgentInstall() as unknown as Captured<
      { connectionId: string; body: unknown; idempotencyKey: string }, unknown>;
    const data = new FormData();
    for (const [name, value] of Object.entries({
      ssh_host: 'host.example', ssh_port: '22', ssh_user: 'installer', private_key: 'ЗАКРЫТЫЙ-КЛЮЧ', access: 'pasted_key', password: 'пароль',
    })) data.set(name, value);
    const reading = readInstall(data);
    if (!reading.ok) throw new Error('the form reads');
    await create.mutationFn({ connectionId: CONNECTION, idempotencyKey: 'ik-install', body: reading.body });
    expect(requests).toHaveLength(1);
    const sent = requests[0]?.body ?? '';
    expect(JSON.parse(sent)).toEqual({ ssh_host: 'host.example', ssh_port: 22, ssh_user: 'installer', access: 'generated_key' });
    for (const forbidden of ['private_key', 'ЗАКРЫТЫЙ-КЛЮЧ', 'pasted_key', 'password', 'пароль']) {
      expect(sent, forbidden).not.toContain(forbidden);
    }
  });

  it('confirms the fingerprint by value, to the install’s own address', async () => {
    fallback = { status: 200, body: { install_id: INSTALL } };
    const confirm = useConfirmExecutorAgentInstallHostKey() as unknown as Captured<
      { connectionId: string; installId: string; hostKeyFingerprint: string; idempotencyKey: string }, unknown>;
    expect(confirm.retry).toBe(false);
    await confirm.mutationFn({
      connectionId: CONNECTION, installId: INSTALL, hostKeyFingerprint: 'SHA256:abc', idempotencyKey: 'ik-confirm',
    });
    expect(requests).toEqual([{
      method: 'POST', path: `/bff/v1/executor-connections/${CONNECTION}/agent-installs/${INSTALL}/confirm-host-key`,
      body: '{"host_key_fingerprint":"SHA256:abc"}', key: 'ik-confirm',
    }]);
  });

  it('sets and clears the administrator’s mark with one operation, saying which', async () => {
    fallback = { status: 200, body: {} };
    const mark = useSetExecutorIntegrationAuthorisation() as unknown as Captured<
      { connectionId: string; authorised: boolean; idempotencyKey: string }, unknown>;
    expect(mark.retry).toBe(false);
    await mark.mutationFn({ connectionId: CONNECTION, authorised: true, idempotencyKey: 'ik-on' });
    await mark.mutationFn({ connectionId: CONNECTION, authorised: false, idempotencyKey: 'ik-off' });
    expect(requests).toEqual([
      { method: 'POST', path: `/bff/v1/executor-connections/${CONNECTION}/integration-authorisation`, body: '{"authorised":true}', key: 'ik-on' },
      { method: 'POST', path: `/bff/v1/executor-connections/${CONNECTION}/integration-authorisation`, body: '{"authorised":false}', key: 'ik-off' },
    ]);
  });
});

const IDENTITY = { displayName: 'Агент распознавания', pinId: 'модель-основная', gatewayModel: 'шлюзовая-основная' };
const AGENT_SPEC = { kind: 'pull', displayName: IDENTITY.displayName, body: agentRevisionRequest(IDENTITY) } as const;

describe('a connection is created once and reused (both paths, and the OpenRouter preset)', () => {
  it('creates a pull connection and saves its first revision as an agent, each under its own key', async () => {
    answers = [{ status: 201, body: { connection_id: CONNECTION } }, { status: 201, body: { revision_no: 1 } }];
    const { ensure } = useEnsureConnection();
    expect(await ensure(AGENT_SPEC)).toBe(CONNECTION);
    expect(requests.map((request) => [request.method, request.path])).toEqual([
      ['POST', '/bff/v1/executor-connections'],
      ['POST', `/bff/v1/executor-connections/${CONNECTION}/revisions`],
    ]);
    expect(JSON.parse(requests[0]?.body ?? '{}')).toEqual({ kind: 'pull', display_name: IDENTITY.displayName });
    expect(JSON.parse(requests[1]?.body ?? '{}')).toEqual({
      pin_id: 'модель-основная', gateway_model: 'шлюзовая-основная', billing: 'not_metered', allow_client_documents: false,
      timeout_seconds: 120, pull_client: 'agent', answer_deadline_seconds: 600, max_claimed_tasks: 1,
    });
    expect(requests[0]?.key).not.toBe(requests[1]?.key);
    expect(requests.every((request) => request.key !== null)).toBe(true);
  });

  it('returns the same connection on a second call and sends nothing: a retry never makes a duplicate', async () => {
    answers = [{ status: 201, body: { connection_id: CONNECTION } }, { status: 201, body: {} }];
    const { ensure, madeId } = useEnsureConnection();
    expect(madeId()).toBeNull();
    const one = await ensure(AGENT_SPEC);
    const two = await ensure(AGENT_SPEC);
    expect(two).toBe(one);
    expect(requests).toHaveLength(2);
    expect(madeId()).toBe(CONNECTION);
  });

  it('after a refused revision saves the settings onto the same connection and creates no second one', async () => {
    answers = [
      { status: 201, body: { connection_id: CONNECTION } },
      { status: 422, body: {
        contract_version: CONTRACT_VERSION, error_code: 'validation_failed', message: 'Safe.', correlation_id: 'cid-1',
        retryable: false, details: { field: 'pin_id', constraint: 'model_not_pinned' },
      } },
      { status: 201, body: {} },
    ];
    const { ensure } = useEnsureConnection();
    await expect(ensure(AGENT_SPEC)).rejects.toBeDefined();
    expect(await ensure(AGENT_SPEC)).toBe(CONNECTION);
    expect(requests.map((request) => request.path)).toEqual([
      '/bff/v1/executor-connections',
      `/bff/v1/executor-connections/${CONNECTION}/revisions`,
      `/bff/v1/executor-connections/${CONNECTION}/revisions`,
    ]);
    // A definite refusal ends that intent: the second try is a new command under a new key.
    expect(requests[1]?.key).not.toBe(requests[2]?.key);
  });

  it('repeats an unknown outcome under the same key, so the repeat is the same command', async () => {
    answers = [{ status: 201, body: { connection_id: CONNECTION } }, { status: 500, body: {} }, { status: 201, body: {} }];
    const { ensure } = useEnsureConnection();
    await expect(ensure(AGENT_SPEC)).rejects.toBeDefined();
    await ensure(AGENT_SPEC);
    expect(requests[1]?.key).not.toBeNull();
    expect(requests[2]?.key).toBe(requests[1]?.key);
  });

  it('makes another connection for another name, and a new revision of the same one for other settings', async () => {
    const OTHER = connectionId(64);
    answers = [
      { status: 201, body: { connection_id: CONNECTION } }, { status: 201, body: {} },
      { status: 201, body: {} },
      { status: 201, body: { connection_id: OTHER } }, { status: 201, body: {} },
    ];
    const { ensure } = useEnsureConnection();
    await ensure(AGENT_SPEC);
    const sameNameOtherModel = { ...AGENT_SPEC, body: agentRevisionRequest({ ...IDENTITY, gatewayModel: 'другое-имя' }) };
    expect(await ensure(sameNameOtherModel)).toBe(CONNECTION);
    expect(await ensure({ ...AGENT_SPEC, displayName: 'Другое подключение' })).toBe(OTHER);
    expect(requests.map((request) => request.path)).toEqual([
      '/bff/v1/executor-connections',
      `/bff/v1/executor-connections/${CONNECTION}/revisions`,
      `/bff/v1/executor-connections/${CONNECTION}/revisions`,
      '/bff/v1/executor-connections',
      `/bff/v1/executor-connections/${OTHER}/revisions`,
    ]);
  });

  it('creates the OpenRouter preset as an http_api connection with the gateway’s address and the chat format', async () => {
    answers = [{ status: 201, body: { connection_id: CONNECTION } }, { status: 201, body: {} }];
    const { ensure } = useEnsureConnection();
    await ensure({ kind: 'http_api', displayName: 'OpenRouter', body: openRouterRevisionRequest(IDENTITY) });
    expect(JSON.parse(requests[0]?.body ?? '{}')).toEqual({ kind: 'http_api', display_name: 'OpenRouter' });
    expect(JSON.parse(requests[1]?.body ?? '{}')).toEqual({
      pin_id: 'модель-основная', gateway_model: 'шлюзовая-основная', billing: 'metered', allow_client_documents: false,
      timeout_seconds: 120, api_flavour: 'openai_chat', base_url: 'https://openrouter.ai/api/v1', transport: 'direct',
      max_parallel_calls: 1,
    });
    // The key is not on the wire from here at all.
    expect(requests.some((request) => /secret|api_key|"value"/.test(request.path + request.body))).toBe(false);
  });
});

describe('the two re-reads are bounded and end by themselves', () => {
  type Options = {
    queryKey: readonly unknown[];
    enabled?: boolean;
    initialData?: unknown;
    refetchInterval: (query: { state: { data: unknown } }) => number | false;
  };

  it('re-reads an install only while the worker moves it, every three seconds', () => {
    expect(AGENT_INSTALL_POLL_MS).toBe(3000);
    const start = install(CONNECTION, { install_id: INSTALL, state: 'requested' });
    const options = useAgentInstall(CONNECTION, INSTALL, start) as unknown as Options;
    expect(options.initialData).toBe(start);
    expect(options.queryKey.slice(0, 1)).toEqual(queryKeys.execution.all());
    expect(options.queryKey).toEqual(agentInstallQueryKey(INSTALL));
    const interval = (state: Parameters<typeof install>[1]) =>
      options.refetchInterval({ state: { data: install(CONNECTION, state) } });
    for (const moving of ['requested', 'scanning', 'installing'] as const) {
      expect(interval({ state: moving }), moving).toBe(AGENT_INSTALL_POLL_MS);
      expect(installIsMoving(install(CONNECTION, { state: moving }))).toBe(true);
    }
    // The next move is the person’s (confirming the fingerprint), or the session is over.
    for (const still of ['awaiting_host_key', 'succeeded', 'failed'] as const) {
      expect(interval({ state: still }), still).toBe(false);
    }
    expect(options.refetchInterval({ state: { data: undefined } })).toBe(false);
  });

  it('re-reads an agent connection’s detail every five seconds while a grant waits, and stops when it is ready', () => {
    vi.useFakeTimers();
    vi.setSystemTime(NOW);
    expect(AGENT_STATUS_POLL_MS).toBe(5000);
    const options = useAgentStatusPoll(CONNECTION, true) as unknown as Options;
    // The same cache entry the card reads, so the card and the wizard never disagree.
    expect(options.queryKey).toEqual(queryKeys.execution.connection(CONNECTION));
    expect(options.enabled).toBe(true);
    const waiting = agentCase({ n: 63, enrollments: [{ state: 'pending', expires_at: later(10 * MINUTE) }] }).detail;
    const ready = agentCase({ n: 63, tokens: [agentToken(1, CONNECTION)] }).detail;
    expect(options.refetchInterval({ state: { data: waiting } })).toBe(AGENT_STATUS_POLL_MS);
    expect(options.refetchInterval({ state: { data: ready } })).toBe(false);
    expect(options.refetchInterval({ state: { data: undefined } })).toBe(false);
  });

  it('is off for a quiet connection, so a card that is not moving adds no request', () => {
    const options = useAgentStatusPoll(CONNECTION, false) as unknown as Options;
    expect(options.enabled).toBe(false);
  });
});
