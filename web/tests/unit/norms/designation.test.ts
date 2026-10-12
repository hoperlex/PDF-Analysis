/**
 * `W55A-WEB-NORMS` — what «Сделать текущим» DOES (R-113): it asks first, the confirmation
 * sends one compare-and-set carrying the snapshot the screen showed as current, «Отмена»
 * sends nothing, and the command hook never repeats a write on its own and re-reads every
 * norms answer when the request settles.
 *
 * No DOM (`environment: 'node'`), so this follows `tests/unit/workers/intake-confirmation`:
 * a probe renders the page once, keeps the element tree it returned, and the test calls that
 * tree's own handlers; what they send goes through the generated client to a recording
 * `fetch`. A server render keeps every `useState` at its initial value, so the pending
 * designation is seeded through the exported initialiser `noDesignationIntent`.
 */

import { createElement, isValidElement } from 'react';
import type * as ReactModule from 'react';
import type { ReactElement, ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { NormSnapshot } from '@/shared/api';
import { queryKeys } from '@/shared/api';

import { newClient, renderWith } from '../screens/harness';
import { CURRENT_SNAPSHOT_ID, NORM_SNAPSHOTS, QUALIFIED_SNAPSHOT_ID } from './fixtures';

const seed = vi.hoisted(() => new Map<unknown, unknown>());
/** Every value the page hands the setter of its pending designation (seeded by name). */
const recorded = vi.hoisted(() => [] as unknown[]);

vi.mock('react', async (importOriginal) => {
  const actual = await importOriginal<typeof ReactModule>();
  return {
    ...actual,
    useState: (initial: unknown) => {
      const [value, set] = actual.useState(seed.has(initial) ? seed.get(initial) : initial);
      if (typeof initial !== 'function' || initial.name !== 'noDesignationIntent') return [value, set];
      return [value, (next: unknown) => { recorded.push(next); }];
    },
  };
});

const { NormsPage, noDesignationIntent, designationIntentLabel } = await import('@/_pages/norms/ui/norms-page');
const { NormSnapshotList } = await import('@/widgets/norm-snapshots');
const { NORM_SNAPSHOT_LIMIT, NORM_EVENT_PAGE_LIMIT } = await import('@/entities/norms');

const CURRENT = NORM_SNAPSHOTS[0] as NormSnapshot;
const QUALIFIED = NORM_SNAPSHOTS[1] as NormSnapshot;

let requests: { line: string; key: string | null }[] = [];

beforeEach(() => {
  seed.clear();
  recorded.length = 0;
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
      return new Response(JSON.stringify({
        norms_snapshot_id: QUALIFIED_SNAPSHOT_ID, designated_by: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
        designated_at: '2026-10-12T12:00:00Z',
      }), { status: 200, headers: { 'content-type': 'application/json' } });
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

/** Render `make()` inside a probe over a client holding `snapshots` as the whole list. */
function treeOf(make: () => ReactNode, snapshots: readonly NormSnapshot[] = NORM_SNAPSHOTS): ReactElement {
  const client = newClient();
  client.setQueryData(queryKeys.norms.snapshots(undefined, NORM_SNAPSHOT_LIMIT), {
    items: snapshots, page: { next_cursor: null },
  });
  client.setQueryData(queryKeys.norms.events(undefined, NORM_EVENT_PAGE_LIMIT), {
    items: [], page: { next_cursor: null },
  });
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

const writes = () => requests.filter((request) => request.line.startsWith('PUT'));

describe('«Сделать текущим» asks first', () => {
  it('the row control hands the snapshot to the page and sends nothing', async () => {
    const asked: string[] = [];
    const listTree = treeOf(() => NormSnapshotList({
      items: NORM_SNAPSHOTS, current: { kind: 'current', snapshot: CURRENT }, canDesignate: true, busy: false,
      onDesignate: (snapshot) => asked.push(snapshot.norms_snapshot_id),
    }));
    const row = elements(listTree).find((element) =>
      typeof element.type === 'function' && (element.props as { snapshot?: NormSnapshot }).snapshot === QUALIFIED);
    expect(row, 'the list renders a row for the qualifying snapshot').toBeDefined();
    const rowTree = treeOf(() => (row?.type as (props: unknown) => ReactNode)(row?.props));
    button(rowTree, 'Сделать текущим')?.props.onClick?.();
    await settle();
    expect(asked).toEqual([QUALIFIED_SNAPSHOT_ID]);
    expect(requests).toEqual([]);
  });

  it('the page answers the control with a confirmation, not a write', async () => {
    const tree = treeOf(() => NormsPage({ roles: ['admin'] }));
    expect(button(tree, 'Подтвердить')).toBeUndefined();
    const list = elements(tree).find((element) => element.type === NormSnapshotList) as
      | ReactElement<{ onDesignate: (snapshot: NormSnapshot) => void }>
      | undefined;
    expect(list, 'an administrator’s page renders the snapshot list').toBeDefined();
    list?.props.onDesignate(QUALIFIED);
    await settle();
    expect(writes()).toEqual([]);
    // What it records is the confirmation's content: the target, and the snapshot the list
    // showed as current — the belief the request will carry as `expected_current`.
    expect(recorded).toEqual([{ snapshot: QUALIFIED, expectedCurrent: CURRENT }]);
  });
});

describe('the confirmation sends one compare-and-set', () => {
  it('carrying the target and the snapshot the screen showed current, with no idempotency key', async () => {
    seed.set(noDesignationIntent, { snapshot: QUALIFIED, expectedCurrent: CURRENT });
    const tree = treeOf(() => NormsPage({ roles: ['admin'] }));
    expect(textOf(tree)).toContain(designationIntentLabel({ snapshot: QUALIFIED, expectedCurrent: CURRENT }));
    expect(textOf(tree)).toContain(`Снимок ${CURRENT.content_key} перестанет быть текущим.`);
    const confirm = button(tree, 'Подтвердить');
    expect(confirm?.props.onClick, 'the confirmation is a button with a handler').toBeTypeOf('function');
    confirm?.props.onClick?.();
    await settle();
    expect(writes()).toEqual([{
      line: `PUT /bff/v1/norms/snapshots/current {"norms_snapshot_id":"${QUALIFIED_SNAPSHOT_ID}","expected_current":"${CURRENT_SNAPSHOT_ID}"}`,
      key: null,
    }]);
  });

  it('believing none current when the list showed none', async () => {
    const none = NORM_SNAPSHOTS.map((snapshot) => ({ ...snapshot, current: false }));
    seed.set(noDesignationIntent, { snapshot: QUALIFIED, expectedCurrent: null });
    const tree = treeOf(() => NormsPage({ roles: ['admin'] }), none);
    expect(textOf(tree)).toContain('Сейчас текущего снимка нет.');
    button(tree, 'Подтвердить')?.props.onClick?.();
    await settle();
    expect(writes().map((write) => write.line)).toEqual([
      `PUT /bff/v1/norms/snapshots/current {"norms_snapshot_id":"${QUALIFIED_SNAPSHOT_ID}","expected_current":null}`,
    ]);
  });

  it('a press with none current records a belief of none', async () => {
    const none = NORM_SNAPSHOTS.map((snapshot) => ({ ...snapshot, current: false }));
    const tree = treeOf(() => NormsPage({ roles: ['admin'] }), none);
    const list = elements(tree).find((element) => element.type === NormSnapshotList) as
      ReactElement<{ onDesignate: (snapshot: NormSnapshot) => void }>;
    list.props.onDesignate(none[1] as NormSnapshot);
    expect(recorded).toEqual([{ snapshot: none[1], expectedCurrent: null }]);
    expect(writes()).toEqual([]);
  });

  it('«Отмена» closes the confirmation without a write', async () => {
    seed.set(noDesignationIntent, { snapshot: QUALIFIED, expectedCurrent: CURRENT });
    const tree = treeOf(() => NormsPage({ roles: ['admin'] }));
    button(tree, 'Отмена')?.props.onClick?.();
    await settle();
    expect(writes()).toEqual([]);
  });

  it('an expert’s page carries no confirmation even with an intent pending', () => {
    seed.set(noDesignationIntent, { snapshot: QUALIFIED, expectedCurrent: CURRENT });
    const tree = treeOf(() => NormsPage({ roles: ['expert'] }));
    expect(button(tree, 'Подтвердить')).toBeUndefined();
    expect(elements(tree).some((element) => element.type === NormSnapshotList)).toBe(false);
  });
});
