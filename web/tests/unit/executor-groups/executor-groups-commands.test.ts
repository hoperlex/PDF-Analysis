/**
 * `EXEC2-WEB-GROUPS-01` — the commands on groups, rules and the routing mode, read off the network.
 *
 * The hooks are called with `@tanstack/react-query` replaced by a pass-through, so each `mutationFn`
 * runs the real generated client against a recording `fetch`. What is asserted is what a stand would
 * see: the operation, the path, the JSON body, the caller’s idempotency key on every send, no automatic
 * retry, the whole `execution` root refreshed after a success, and nothing about the dashboard. Written
 * under `R-149d` and not run in EXEC-2; none of it needs PostgreSQL.
 *
 * The cut-over body is the one the contract fixes: `rules` carries the digest that was shown and the
 * mapping, `legacy` carries neither.
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
  useArchiveExecutorGroup,
  useCreateExecutorGroup,
  useReviseExecutorGroup,
  useSetExecutorRoutingMode,
  useSetExecutorRoutingRule,
} from '@/features/manage-executor-group';

const GROUP = 'exg_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const REVISION = 'exgr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const CONNECTION = 'exc_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const CONNECTION_REVISION = 'excr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';

interface Captured<T, U> {
  mutationFn: (input: T) => Promise<U>;
  onSuccess: (result: U) => void;
  retry: boolean;
}

let requests: { method: string; path: string; body: string; key: string | null }[] = [];

beforeEach(() => {
  calls.invalidations.length = 0;
  requests = [];
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
      return new Response(JSON.stringify({}), { status: 200, headers: { 'content-type': 'application/json' } });
    }),
  );
});

const MEMBERS = [{ connection_id: CONNECTION, connection_revision_id: CONNECTION_REVISION }];

describe('a group', () => {
  it('is created with the whole request under the caller’s key, and sent again under the same one', async () => {
    const create = useCreateExecutorGroup() as unknown as Captured<{ body: unknown; idempotencyKey: string }, unknown>;
    expect(create.retry).toBe(false);
    const body = { display_name: 'Группа', pin_id: 'модель', gateway_model: 'имя', billing: 'metered', members: MEMBERS };
    await create.mutationFn({ body, idempotencyKey: 'ik-create' });
    await create.mutationFn({ body, idempotencyKey: 'ik-create' });
    expect(requests).toEqual([
      { method: 'POST', path: '/bff/v1/executor-groups', body: JSON.stringify(body), key: 'ik-create' },
      { method: 'POST', path: '/bff/v1/executor-groups', body: JSON.stringify(body), key: 'ik-create' },
    ]);
  });

  it('gains a revision at the path of the group, with the full settings and no name', async () => {
    const revise = useReviseExecutorGroup() as unknown as Captured<
      { groupId: string; body: unknown; idempotencyKey: string }, unknown>;
    expect(revise.retry).toBe(false);
    const body = { pin_id: 'модель', gateway_model: 'имя', billing: 'metered', members: MEMBERS };
    await revise.mutationFn({ groupId: GROUP, body, idempotencyKey: 'ik-revise' });
    expect(requests).toEqual([
      { method: 'POST', path: `/bff/v1/executor-groups/${GROUP}/revisions`, body: JSON.stringify(body), key: 'ik-revise' },
    ]);
    expect(requests[0]?.body).not.toContain('display_name');
  });

  it('is archived at its own path, with no body', async () => {
    const archive = useArchiveExecutorGroup() as unknown as Captured<{ groupId: string; idempotencyKey: string }, unknown>;
    expect(archive.retry).toBe(false);
    await archive.mutationFn({ groupId: GROUP, idempotencyKey: 'ik-archive' });
    expect(requests).toEqual([
      { method: 'POST', path: `/bff/v1/executor-groups/${GROUP}/archive`, body: '', key: 'ik-archive' },
    ]);
  });
});

describe('a rule', () => {
  it('names a work kind in the path and a group revision in the body', async () => {
    const rule = useSetExecutorRoutingRule() as unknown as Captured<
      { workKind: string; groupRevisionId: string; idempotencyKey: string }, unknown>;
    expect(rule.retry).toBe(false);
    await rule.mutationFn({ workKind: 'comparison_spec', groupRevisionId: REVISION, idempotencyKey: 'ik-rule' });
    expect(requests).toEqual([
      {
        method: 'PUT', path: '/bff/v1/executor-routing-rules/comparison_spec',
        body: JSON.stringify({ group_revision_id: REVISION }), key: 'ik-rule',
      },
    ]);
  });
});

describe('the routing mode', () => {
  it('goes to rules with the digest that was shown and the mapping', async () => {
    const mode = useSetExecutorRoutingMode() as unknown as Captured<{ body: unknown; idempotencyKey: string }, unknown>;
    expect(mode.retry).toBe(false);
    const body = {
      mode: 'rules',
      preview_digest: 'b'.repeat(64),
      mapping: [{ work_kind: 'text_analysis', group_display_name: 'Группа правила' }],
    };
    await mode.mutationFn({ body, idempotencyKey: 'ik-mode' });
    expect(requests).toEqual([
      { method: 'POST', path: '/bff/v1/executor-routing/mode', body: JSON.stringify(body), key: 'ik-mode' },
    ]);
  });

  it('goes back to legacy with neither the digest nor the mapping', async () => {
    const mode = useSetExecutorRoutingMode() as unknown as Captured<{ body: unknown; idempotencyKey: string }, unknown>;
    await mode.mutationFn({ body: { mode: 'legacy' }, idempotencyKey: 'ik-back' });
    expect(requests).toEqual([
      { method: 'POST', path: '/bff/v1/executor-routing/mode', body: '{"mode":"legacy"}', key: 'ik-back' },
    ]);
    expect(requests[0]?.body).not.toContain('preview_digest');
    expect(requests[0]?.body).not.toContain('mapping');
  });
});

describe('after a success', () => {
  it('refreshes every execution read, and only those: no number the dashboard reads changes', () => {
    for (const hook of [
      useCreateExecutorGroup, useReviseExecutorGroup, useArchiveExecutorGroup,
      useSetExecutorRoutingRule, useSetExecutorRoutingMode,
    ]) {
      calls.invalidations.length = 0;
      (hook() as unknown as Captured<unknown, unknown>).onSuccess({});
      expect(calls.invalidations).toEqual([[{ queryKey: queryKeys.execution.all() }]]);
      expect(JSON.stringify(calls.invalidations)).not.toContain('dashboard');
    }
  });
});
