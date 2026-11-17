/**
 * `UI-B-51`, `UI-B-69`: the original's «Активные / Завершённые / Ошибки» over the queue, as a strip of the queue's states with
 * their counts, set on the same address the «Состояние задачи» select sets.
 *
 * Held here, each with a case that shows it can fail:
 *
 *   - every one of the eight states is in exactly one group, so the three captions add up to «Все»;
 *   - the strip draws the server's overview and nothing else: the group totals and the total are sums of the overview, a state without
 *     a job is not drawn, except the one the list is narrowed to;
 *   - the pressed state is the address's, and «Все» is pressed with no state;
 *   - the page draws the strip only where the page carries an overview, beside the filters («Фильтры ▾»), and not in place of them;
 *   - a state alone in its group is not drawn beside the group's press (`UIP-S13-02`), unless the list is narrowed to it.
 */

import { createElement } from 'react';
import type { ComponentType } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { ExecutionQueueStateCount } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { QUEUE_STATE_GROUPS, QUEUE_STATE_OPTIONS, jobStateLabel } from '@/entities/execution';
import type { ExecutionQueueState } from '@/entities/execution';
import { QueuePage } from '@/_pages/queue';
import type { QueuePageProps } from '@/_pages/queue';
import { QueueStateStrip } from '@/widgets/execution-queue';

import { newClient, renderScreen } from '../screens/harness';

const noop = (): void => {};

const OVERVIEW: readonly ExecutionQueueStateCount[] = [
  { state: 'queued', count: 3 }, { state: 'leased', count: 0 }, { state: 'running', count: 1 },
  { state: 'retry_wait', count: 0 }, { state: 'succeeded', count: 12 }, { state: 'failed', count: 2 },
  { state: 'cancelled', count: 0 }, { state: 'dead_letter', count: 0 },
];

function strip(selected: ExecutionQueueState | '' = '', overview: readonly ExecutionQueueStateCount[] = OVERVIEW): string {
  return renderToStaticMarkup(createElement(QueueStateStrip, { overview, selected, onSelect: noop }));
}

describe('the groups', () => {
  it('hold every state once', () => {
    const grouped = QUEUE_STATE_GROUPS.flatMap((group) => group.states);
    expect([...grouped].sort()).toEqual(QUEUE_STATE_OPTIONS.map((option) => option.value).sort());
    expect(new Set(grouped).size).toBe(grouped.length);
  });

  it('are the original’s three headings', () => {
    expect(QUEUE_STATE_GROUPS.map((group) => group.label)).toEqual(['Активные', 'Завершённые', 'Ошибки']);
    expect(QUEUE_STATE_GROUPS.find((group) => group.key === 'errors')?.states).toEqual(['failed', 'dead_letter']);
    expect(QUEUE_STATE_GROUPS.find((group) => group.key === 'active')?.states).toContain('running');
  });
});

describe('the strip', () => {
  it('says each group with its total, and «Все» with the whole', () => {
    const markup = strip();
    expect(markup).toContain('Активные 4');
    expect(markup).toContain('Завершённые 12');
    expect(markup).toContain('Ошибки 2');
    expect(markup).toContain('Все 18');
    expect(markup).toContain('data-queue-group="active" data-queue-group-total="4"');
    expect(markup).toContain('data-queue-group="errors" data-queue-group-total="2"');
  });

  it('draws a press for each state that has a job, labelled as the row labels it, and none for the others', () => {
    // `UIP-S13-02`: a state alone in its group is the group's own press («Завершённые 12» is «Завершена 12»); only a group with two
    // states that have a job draws them. Here the active group has two (queued and running), the other two groups have one each.
    const markup = strip();
    for (const state of ['queued', 'running'] as const) {
      expect(markup).toContain(`data-queue-state-chip="${state}"`);
      expect(markup).toContain(`${jobStateLabel(state)} ${OVERVIEW.find((entry) => entry.state === state)?.count}`);
    }
    for (const state of ['leased', 'retry_wait', 'cancelled', 'dead_letter', 'succeeded', 'failed'] as const) {
      expect(markup).not.toContain(`data-queue-state-chip="${state}"`);
    }
  });

  it('draws the states of a group that holds two with a job, and none of a group that holds one', () => {
    const two = strip('', OVERVIEW.map((entry) => (entry.state === 'dead_letter' ? { ...entry, count: 4 } : entry)));
    expect(two).toContain('data-queue-state-chip="failed"');
    expect(two).toContain('data-queue-state-chip="dead_letter"');
    expect(two).toContain('Ошибки 6');
    // «Ошибки 2» alone: no «Ошибка 2» beside it.
    expect(strip()).toContain('Ошибки 2');
    expect(strip()).not.toContain('Ошибка 2');
  });

  it('draws the state the list is narrowed to even without a job, so a filter shows what it is', () => {
    const markup = strip('dead_letter');
    expect(markup).toContain('data-queue-state-chip="dead_letter"');
    expect(markup).toMatch(/aria-pressed="true"[^>]*data-queue-state-chip="dead_letter"/);
    expect(markup).toContain('data-queue-state-total="0"');
  });

  it('draws the lone state the list is narrowed to, pressed, though it is alone in its group', () => {
    const markup = strip('failed');
    expect(markup).toMatch(/aria-pressed="true"[^>]*data-queue-state-chip="failed"/);
  });

  it('presses «Все» with no state, and the state otherwise', () => {
    expect(strip('')).toMatch(/aria-pressed="true"[^>]*data-queue-state-chip=""[^>]*>Все 18/);
    const failed = strip('failed');
    expect(failed).toMatch(/aria-pressed="false"[^>]*data-queue-state-chip=""[^>]*>Все 18/);
    expect(failed).toMatch(/aria-pressed="true"[^>]*data-queue-state-chip="failed"/);
    expect(failed.match(/aria-pressed="true"/g)).toHaveLength(1);
  });

  it('counts an empty queue as «Все 0» with no state press', () => {
    const markup = strip('', OVERVIEW.map((entry) => ({ ...entry, count: 0 })));
    expect(markup).toContain('Все 0');
    expect(markup).not.toMatch(/data-queue-state-chip="[a-z_]+"/);
    expect(markup).toContain('Активные 0');
  });

  it('adds up: the group totals are the total', () => {
    const totals = [...strip().matchAll(/data-queue-group-total="(\d+)"/g)].map((match) => Number(match[1]));
    expect(totals.reduce((sum, value) => sum + value, 0)).toBe(OVERVIEW.reduce((sum, entry) => sum + entry.count, 0));
  });
});

describe('the page', () => {
  const PAGE = { items: [], page: { next_cursor: null }, paused: false };
  const render = (overview: readonly ExecutionQueueStateCount[] | undefined, state: ExecutionQueueState | '' = '') => {
    const client = newClient();
    client.setQueryData(
      queryKeys.execution.queue(undefined, state === '' ? {} : { state }),
      overview === undefined ? PAGE : { ...PAGE, overview },
    );
    return renderScreen(client, createElement(QueuePage as ComponentType<QueuePageProps>, { initialAddress: { state, period: 'all' } }));
  };

  it('draws the strip beside «Фильтры ▾» when the page carries an overview', () => {
    const markup = render(OVERVIEW);
    expect(markup).toContain('data-queue-state-strip');
    expect(markup).toContain('Активные 4');
    expect(markup).toContain('data-queue-state-filter');
  });

  it('presses the state the address names', () => {
    const markup = render(OVERVIEW, 'failed');
    expect(markup).toMatch(/aria-pressed="true"[^>]*data-queue-state-chip="failed"/);
    expect(markup).toMatch(/<option value="failed" selected="">/);
  });

  it('draws no strip where the page carries no overview, and the filters still stand', () => {
    const markup = render(undefined);
    expect(markup).not.toContain('data-queue-state-strip');
    expect(markup).toContain('data-queue-state-filter');
  });
});
