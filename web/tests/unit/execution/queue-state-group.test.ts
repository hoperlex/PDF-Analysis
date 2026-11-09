/**
 * `D-370` (contract 1.43.0): the queue's «Активные / Завершённые / Ошибки» list the WHOLE group.
 *
 * Lane P10 drew the three groups as captions over single-state presses, because the server filtered by one state and a client-side
 * merge of several single-state pages would be a silent partial list. `listExecutionQueue` now takes `state_group`, so a group's
 * caption is a press that lists every job of the group: one paged, counted list.
 *
 * Held here, each with a case that shows it can fail:
 *
 *   - the address keeps a group (`?group=errors`) next to the state: read with the closed set enforced, a state wins over a group
 *     (the server refuses both), written so that one drops the other;
 *   - the web's three groups are the server's: the same names as the contract's `state_group` enum and the same states as
 *     `execution.public.QUEUE_STATE_GROUPS` (read from its source, so one cannot move without the other);
 *   - the strip draws a group's caption as a press when the page can act on it, and as a caption when it cannot;
 *   - the page opened on a group reads the group's queue, in its own cache entry, and asks the server with `state_group`.
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { createElement } from 'react';
import type { ComponentType } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { ExecutionQueueStateCount } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { QUEUE_STATE_GROUPS, queueQueryOptions } from '@/entities/execution';
import type { ExecutionQueueState } from '@/entities/execution';
import {
  EMPTY_QUEUE_ADDRESS, QUEUE_GROUP_PARAM, QueuePage, isQueueGroup, readQueueAddress, writeQueueAddress,
} from '@/_pages/queue';
import type { QueuePageProps } from '@/_pages/queue';
import { QueueStateStrip } from '@/widgets/execution-queue';

import { newClient, renderScreen } from '../screens/harness';

const noop = (): void => {};
const read = (query: string) => readQueueAddress(new URLSearchParams(query));

const OVERVIEW: readonly ExecutionQueueStateCount[] = [
  { state: 'queued', count: 3 }, { state: 'leased', count: 0 }, { state: 'running', count: 1 },
  { state: 'retry_wait', count: 0 }, { state: 'succeeded', count: 12 }, { state: 'failed', count: 2 },
  { state: 'cancelled', count: 0 }, { state: 'dead_letter', count: 1 },
];

describe('the address keeps a group beside the state', () => {
  it('reads the three groups and drops a name outside them', () => {
    expect(read('group=errors')).toEqual({ state: '', group: 'errors', period: 'all' });
    for (const group of ['active', 'completed', 'errors'] as const) expect(read(`group=${group}`).group).toBe(group);
    expect(read('group=exploded')).toEqual(EMPTY_QUEUE_ADDRESS);
    expect(read('group=ERRORS').group).toBeUndefined();
    expect(read('group=')).toEqual(EMPTY_QUEUE_ADDRESS);
    expect(isQueueGroup('errors')).toBe(true);
    expect(isQueueGroup('failed')).toBe(false);
  });

  it('reads a state over a group when a link names both: the server refuses the two together', () => {
    expect(read('state=failed&group=errors')).toEqual({ state: 'failed', period: 'all' });
  });

  it('writes a group and drops the state it replaces, and writes a state and drops the group it replaces', () => {
    expect(writeQueueAddress(new URLSearchParams('state=failed'), { state: '', group: 'errors', period: 'all' }).toString()).toBe('group=errors');
    expect(writeQueueAddress(new URLSearchParams('group=errors'), { state: 'queued', period: 'all' }).toString()).toBe('state=queued');
    // Even a caller that hands both writes the state alone: an address never names both.
    expect(writeQueueAddress(new URLSearchParams(''), { state: 'queued', group: 'errors', period: 'week' }).toString()).toBe('state=queued&period=week');
    expect(writeQueueAddress(new URLSearchParams('group=errors&period=week'), EMPTY_QUEUE_ADDRESS).toString()).toBe('');
    expect(writeQueueAddress(new URLSearchParams('project=prj_X'), { state: '', group: 'active', period: 'all' }).get('project')).toBe('prj_X');
  });

  it('round-trips every group, with the period', () => {
    for (const group of QUEUE_STATE_GROUPS) {
      const written = writeQueueAddress(new URLSearchParams(''), { state: '', group: group.key, period: 'month' });
      expect(written.get(QUEUE_GROUP_PARAM)).toBe(group.key);
      expect(readQueueAddress(written)).toEqual({ state: '', group: group.key, period: 'month' });
    }
  });
});

describe('the web’s groups are the server’s', () => {
  const root = resolve(__dirname, '../../../..');

  it('are the names of the contract’s `state_group` enum', () => {
    const contract = JSON.parse(readFileSync(resolve(root, 'contracts/api/v1/openapi.json'), 'utf8')) as {
      paths: Record<string, { get: { parameters: { name?: string; schema?: { enum?: string[] } }[] } }>;
    };
    const parameter = contract.paths['/execution/queue']?.get.parameters.find((one) => one.name === 'state_group');
    expect(parameter?.schema?.enum).toEqual(QUEUE_STATE_GROUPS.map((group) => group.key));
  });

  it('hold the states `execution.public.QUEUE_STATE_GROUPS` holds', () => {
    const source = readFileSync(resolve(root, 'src/auditmanager/execution/public.py'), 'utf8');
    const block = /QUEUE_STATE_GROUPS: Mapping\[str, tuple\[str, \.\.\.\]\] = \{([\s\S]*?)\n\}/.exec(source)?.[1] ?? '';
    const server = Object.fromEntries(
      [...block.matchAll(/"(\w+)":\s*\(([^)]*)\)/g)].map((match) => [match[1], [...(match[2] ?? '').matchAll(/"(\w+)"/g)].map((one) => one[1])]),
    );
    expect(Object.keys(server)).toEqual(QUEUE_STATE_GROUPS.map((group) => group.key));
    for (const group of QUEUE_STATE_GROUPS) expect(server[group.key], group.key).toEqual([...group.states]);
  });
});

describe('the strip', () => {
  const strip = (props: { selectedGroup?: 'active' | 'completed' | 'errors' | ''; selected?: ExecutionQueueState | ''; withGroups?: boolean }) =>
    renderToStaticMarkup(createElement(QueueStateStrip, {
      overview: OVERVIEW,
      selected: props.selected ?? '',
      ...(props.selectedGroup === undefined ? {} : { selectedGroup: props.selectedGroup }),
      onSelect: noop,
      ...(props.withGroups === false ? {} : { onSelectGroup: noop }),
    }));

  it('draws a group’s caption as a press with the group’s total, and lists what it lists in its title', () => {
    const markup = strip({});
    for (const [key, label, total] of [['active', 'Активные', 4], ['completed', 'Завершённые', 12], ['errors', 'Ошибки', 3]] as const) {
      expect(markup).toMatch(new RegExp(`data-queue-group-chip="${key}"[^>]*>${label} ${total}</button>`));
      expect(markup).toContain(`data-queue-group="${key}" data-queue-group-total="${total}"`);
    }
    expect(markup).toContain('title="Показать все задачи группы: ');
  });

  it('presses the group the address names and «Все» no longer', () => {
    const markup = strip({ selectedGroup: 'errors' });
    expect(markup).toMatch(/aria-pressed="true"[^>]*data-queue-group-chip="errors"/);
    expect(markup).toMatch(/aria-pressed="false"[^>]*data-queue-group-chip="active"/);
    expect(markup).toMatch(/aria-pressed="false"[^>]*data-queue-state-chip=""[^>]*>Все 19/);
    expect(markup.match(/aria-pressed="true"/g)).toHaveLength(1);
    // With nothing chosen, «Все» is the pressed one.
    expect(strip({})).toMatch(/aria-pressed="true"[^>]*data-queue-state-chip=""[^>]*>Все 19/);
  });

  it('can fail: where the page offers no group press the caption stays a caption', () => {
    const markup = strip({ withGroups: false });
    expect(markup).not.toContain('data-queue-group-chip');
    expect(markup).toContain('Ошибки 3');
  });
});

describe('the page opened on a group', () => {
  const PAGE = { items: [], page: { next_cursor: null }, paused: false, overview: OVERVIEW, live_failure_count: 0 };

  it('reads the group’s queue, never the unfiltered one, and presses the group', () => {
    const client = newClient();
    client.setQueryData(queryKeys.execution.queue(undefined, { stateGroup: 'errors' }), PAGE);
    const markup = renderScreen(client, createElement(QueuePage as ComponentType<QueuePageProps>, { initialAddress: { state: '', group: 'errors', period: 'all' } }));
    const keys = client.getQueryCache().getAll().map((query) => JSON.stringify(query.queryKey));
    expect(keys).toContain(JSON.stringify(queryKeys.execution.queue(undefined, { stateGroup: 'errors' })));
    expect(keys).not.toContain(JSON.stringify(queryKeys.execution.queue(undefined, {})));
    expect(markup).toMatch(/aria-pressed="true"[^>]*data-queue-group-chip="errors"/);
    // The state select shows «Все состояния»: a group is not one of its states.
    expect(markup).toMatch(/<option value="" selected="">/);
  });

  it('keeps a group’s cache entry apart from the entry of the state, and of no filter', () => {
    const group = JSON.stringify(queryKeys.execution.queue(undefined, { stateGroup: 'errors' }));
    expect(group).not.toBe(JSON.stringify(queryKeys.execution.queue(undefined, { state: 'failed' })));
    expect(group).not.toBe(JSON.stringify(queryKeys.execution.queue(undefined, {})));
    expect(group).not.toBe(JSON.stringify(queryKeys.execution.queue(undefined, { stateGroup: 'active' })));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it('asks the server for the group with `state_group`, and for a state with `state`, never both', async () => {
    const asked: URL[] = [];
    vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', '/bff/v1');
    vi.stubGlobal('fetch', async (input: RequestInfo | URL) => {
      asked.push(new URL(String(input), 'http://web.test'));
      return new Response(JSON.stringify(PAGE), { status: 200, headers: { 'content-type': 'application/json' } });
    });
    await (queueQueryOptions(undefined, { stateGroup: 'errors', createdFrom: '2026-11-01T00:00:00Z' }).queryFn as () => Promise<unknown>)();
    await (queueQueryOptions(undefined, { state: 'failed' }).queryFn as () => Promise<unknown>)();
    expect(asked).toHaveLength(2);
    const [group, state] = asked as [URL, URL];
    expect(group.searchParams.get('state_group')).toBe('errors');
    expect(group.searchParams.has('state')).toBe(false);
    expect(group.searchParams.get('created_from')).toBe('2026-11-01T00:00:00Z');
    expect(state.searchParams.get('state')).toBe('failed');
    expect(state.searchParams.has('state_group')).toBe(false);
  });
});
