/**
 * `W54-WORKERS-WEB` — what the intake switch *does* when pressed.
 *
 * No DOM here (`environment: 'node'`), so this follows
 * `tests/unit/widgets/identity-actions.test.ts`: a probe renders the control once, keeps the
 * element tree it returned, and the test calls that tree's own handlers. What they send goes
 * through the generated client to a recording `fetch`, so "the switch sends nothing" and
 * "the confirmation sends the one key" are read off the network.
 *
 * A server render keeps every `useState` at its initial value. The page's pending intent is
 * initialised by the exported `noIntakeIntent`, and the `react` mock below substitutes a
 * seeded intent for exactly that initialiser and changes nothing else.
 */

import { createElement, isValidElement } from 'react';
import type * as ReactModule from 'react';
import type { ReactElement, ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { ExecutionWorker } from '@/shared/api';
import { queryKeys } from '@/shared/api';

import { newClient, renderWith } from '../screens/harness';

const seed = vi.hoisted(() => new Map<unknown, unknown>());

vi.mock('react', async (importOriginal) => {
  const actual = await importOriginal<typeof ReactModule>();
  return {
    ...actual,
    useState: (initial: unknown) => actual.useState(seed.has(initial) ? seed.get(initial) : initial),
  };
});

const { WorkersPage, noIntakeIntent } = await import('@/_pages/workers/ui/workers-page');
const { WorkerList } = await import('@/widgets/worker-list');
const { WORKER_PAGE_LIMIT } = await import('@/entities/execution');

const WORKER: ExecutionWorker = {
  worker_id: 'wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8A',
  state: 'online',
  intake_enabled: true,
  slots: 1,
  version: '0.5.0',
  started_at: '2026-10-12T10:00:00Z',
  heartbeat_at: '2026-10-12T10:05:00Z',
  current_run_ids: [],
};

let requests: { line: string; key: string | null }[] = [];

beforeEach(() => {
  seed.clear();
  requests = [];
  vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', 'http://web.test/bff/v1');
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string, init: RequestInit) => {
      const url = new URL(input);
      const headers = new Headers(init.headers);
      requests.push({
        line: `${init.method ?? 'GET'} ${url.pathname}${init.body ? ` ${String(init.body)}` : ''}`,
        key: headers.get('Idempotency-Key'),
      });
      return new Response(JSON.stringify({ ...WORKER, intake_enabled: false }), {
        status: 200, headers: { 'content-type': 'application/json' },
      });
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

/** Render `make()` inside a probe over a client seeded as an administrator's page. */
function treeOf(make: () => ReactNode): ReactElement {
  const client = newClient();
  client.setQueryData(queryKeys.execution.workers(undefined, WORKER_PAGE_LIMIT), {
    items: [WORKER], page: { next_cursor: null },
  });
  client.setQueryData(queryKeys.account.me(), { roles: ['admin'] });
  let tree: ReactNode = null;
  function Probe() {
    tree = make();
    return tree as ReactElement;
  }
  renderWith(client, createElement(Probe));
  expect(isValidElement(tree)).toBe(true);
  return tree as unknown as ReactElement;
}

function elements(node: ReactNode): ReactElement[] {
  if (Array.isArray(node)) return node.flatMap(elements);
  if (!isValidElement(node)) return [];
  const props = node.props as { children?: ReactNode };
  return [node, ...elements(props.children)];
}

function textOf(node: ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(textOf).join('');
  if (!isValidElement(node)) return '';
  return textOf((node.props as { children?: ReactNode }).children);
}

function button(tree: ReactElement, text: string): ReactElement<{ onClick?: () => void }> | undefined {
  return elements(tree).find((element) => element.type === 'button' && textOf(element) === text) as
    | ReactElement<{ onClick?: () => void }>
    | undefined;
}

async function settle(): Promise<void> {
  for (let i = 0; i < 5; i += 1) await new Promise((resolve) => setTimeout(resolve, 0));
}

describe('the intake switch asks first', () => {
  it('the row switch hands the worker and the opposite intake to the page, and sends nothing', async () => {
    const asked: [string, boolean][] = [];
    // The list's rows are components of their own, so the switch is reached in the row's tree.
    const listTree = treeOf(() => WorkerList({
      items: [WORKER], roles: ['admin'], busy: false,
      onIntake: (worker, enabled) => asked.push([worker.worker_id, enabled]),
      onNext: null, onPrevious: null,
    }));
    const row = elements(listTree).find((element) => typeof element.type === 'function' && (element.props as { worker?: ExecutionWorker }).worker === WORKER);
    expect(row, 'the list renders a row for the worker').toBeDefined();
    const rowTree = treeOf(() => (row?.type as (props: unknown) => ReactNode)(row?.props));
    button(rowTree, 'Не брать новые')?.props.onClick?.();
    await settle();
    expect(asked).toEqual([[WORKER.worker_id, false]]);
    expect(requests).toEqual([]);
  });

  it('the page answers the switch with a confirmation, not a write', async () => {
    const tree = treeOf(() => WorkersPage());
    expect(button(tree, 'Подтвердить')).toBeUndefined();
    const list = elements(tree).find((element) => element.type === WorkerList) as
      | ReactElement<{ onIntake: (worker: ExecutionWorker, enabled: boolean) => void }>
      | undefined;
    expect(list, 'the page renders the worker list').toBeDefined();
    list?.props.onIntake(WORKER, false);
    await settle();
    expect(requests.filter((request) => request.line.startsWith('PUT'))).toEqual([]);
  });

  it('the confirmation sends one setWorkerIntake with the intent key, and a repeat reuses it', async () => {
    seed.set(noIntakeIntent, { worker: WORKER, enabled: false, key: 'ik-seeded-intent' });
    const tree = treeOf(() => WorkersPage());
    expect(textOf(tree)).toContain(`Запретить исполнителю ${WORKER.worker_id} брать новые прогоны?`);
    const confirm = button(tree, 'Подтвердить');
    expect(confirm?.props.onClick, 'the confirmation is a button with a handler').toBeTypeOf('function');
    confirm?.props.onClick?.();
    await settle();
    confirm?.props.onClick?.();
    await settle();
    const writes = requests.filter((request) => request.line.startsWith('PUT'));
    expect(writes).toEqual([
      { line: `PUT /bff/v1/execution/workers/${WORKER.worker_id}/intake {"enabled":false}`, key: 'ik-seeded-intent' },
      { line: `PUT /bff/v1/execution/workers/${WORKER.worker_id}/intake {"enabled":false}`, key: 'ik-seeded-intent' },
    ]);
  });

  it('«Отмена» closes the confirmation without a write', async () => {
    seed.set(noIntakeIntent, { worker: WORKER, enabled: true, key: 'ik-cancelled' });
    const tree = treeOf(() => WorkersPage());
    expect(textOf(tree)).toContain(`Разрешить исполнителю ${WORKER.worker_id} брать новые прогоны?`);
    button(tree, 'Отмена')?.props.onClick?.();
    await settle();
    expect(requests.filter((request) => request.line.startsWith('PUT'))).toEqual([]);
  });
});
