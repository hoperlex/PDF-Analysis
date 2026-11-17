/**
 * `UIP-S13-02`: over the queue's list, the row of «Фильтры ▾» and the chips of the groups, the line of progress «N / M» with the total
 * «✓ N ✗ M» from the overview, and the confirmations that name the document and its version and never a run's number.
 *
 * Held here, each with a case that shows it can fail:
 *
 *   - the line's figures are the overview's, and nothing is drawn for a queue with no job or a page with no overview;
 *   - the state and the period are in «Фильтры ▾» and not beside the chips; the button says how many of them are narrowed;
 *   - a state alone in its group is not drawn beside the group's press («Ошибки 9» and «Ошибка 9»), unless it is the one the list is narrowed to;
 *   - no sentence of a confirmation holds a run's number.
 */

import { createElement } from 'react';
import type { ComponentType } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { ExecutionQueueItem, ExecutionQueueStateCount } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { QueuePage } from '@/_pages/queue';
import type { QueuePageProps } from '@/_pages/queue';
import { intentLabel } from '@/_pages/queue/ui/queue-page';
import { QueueProgress, QueueStateStrip, queueProgress } from '@/widgets/execution-queue';

import { newClient, renderScreen } from '../screens/harness';
import { QUEUE_WORK } from './queue-work';

const noop = (): void => {};

/** The state counts of an overview, the states left out being zero. */
function overview(counts: Partial<Record<ExecutionQueueStateCount['state'], number>>): readonly ExecutionQueueStateCount[] {
  return (['queued', 'leased', 'running', 'retry_wait', 'succeeded', 'failed', 'cancelled', 'dead_letter'] as const)
    .map((state) => ({ state, count: counts[state] ?? 0 }));
}

describe('the line of progress', () => {
  it('counts the jobs that have ended, over all of them, with the ones that ended well and the ones that failed', () => {
    expect(queueProgress(overview({ queued: 2, running: 1, succeeded: 3, failed: 1 })))
      .toEqual({ total: 7, ended: 4, succeeded: 3, failed: 1 });
  });

  it('counts a cancelled job as ended and as neither of the two marks, and a stopped one as failed', () => {
    expect(queueProgress(overview({ succeeded: 2, cancelled: 3, dead_letter: 1 })))
      .toEqual({ total: 6, ended: 6, succeeded: 2, failed: 1 });
  });

  it('is nothing for an empty queue and for a page with no overview', () => {
    expect(queueProgress(overview({}))).toBeNull();
    expect(queueProgress(undefined)).toBeNull();
    expect(renderToStaticMarkup(createElement(QueueProgress, { overview: overview({}) }))).toBe('');
    expect(renderToStaticMarkup(createElement(QueueProgress, { overview: undefined }))).toBe('');
  });

  it('is drawn as «N / M», a bar and «✓ N ✗ M»', () => {
    const markup = renderToStaticMarkup(createElement(QueueProgress, { overview: overview({ queued: 2, succeeded: 3, failed: 1 }) }));
    expect(markup).toContain('data-queue-progress="4/6"');
    expect(markup).toContain('>4 / 6</span>');
    expect(markup).toContain('<progress');
    expect(markup).toContain('value="4"');
    expect(markup).toContain('max="6"');
    expect(markup).toContain('>✓ 3</span>');
    expect(markup).toContain('>✗ 1</span>');
  });
});

describe('the row over the list', () => {
  const PAGE = { items: [], page: { next_cursor: null }, paused: false };
  const render = (counts: Partial<Record<ExecutionQueueStateCount['state'], number>> | undefined, address: QueuePageProps['initialAddress'] = undefined): string => {
    const client = newClient();
    const state = address?.state ?? '';
    client.setQueryData(
      queryKeys.execution.queue(undefined, state === '' ? {} : { state }),
      counts === undefined ? PAGE : { ...PAGE, overview: overview(counts) },
    );
    return renderScreen(client, createElement(QueuePage as ComponentType<QueuePageProps>, address === undefined ? {} : { initialAddress: address }));
  };

  it('draws the line of progress from the page\'s overview', () => {
    const markup = render({ queued: 2, succeeded: 3, failed: 1 });
    expect(markup).toContain('data-queue-progress="4/6"');
  });

  it('draws no line where the page carries no overview', () => {
    expect(render(undefined)).not.toContain('data-queue-progress');
  });

  it('holds the state and the period in «Фильтры ▾», and in nothing else', () => {
    const markup = render({ queued: 1 });
    const panel = /<details[^>]*data-queue-filters[^>]*>[\s\S]*?<\/details>/.exec(markup)?.[0] ?? '';
    expect(panel).toContain('Фильтры');
    expect(panel).toContain('data-queue-state-filter');
    expect(panel).toContain('data-queue-period-filter');
    expect(markup.match(/data-queue-state-filter/g)).toHaveLength(1);
    expect(markup.match(/data-queue-period-filter/g)).toHaveLength(1);
    // The groups are chips beside it, not in it.
    expect(panel).not.toContain('data-queue-group-chip');
    expect(markup).toContain('data-queue-group-chip="active"');
  });

  it('says how many of the two it narrows', () => {
    expect(render({ queued: 1 })).toMatch(/data-queue-filters="0"[^>]*>[\s\S]*?Фильтры <span/);
    expect(render({ failed: 1 }, { state: 'failed', period: 'all' })).toContain('Фильтры (1)');
    expect(render({ failed: 1 }, { state: 'failed', period: 'week' })).toContain('Фильтры (2)');
    expect(render({ failed: 1 }, { state: '', period: 'month' })).toContain('Фильтры (1)');
  });
});

describe('a state alone in its group', () => {
  const strip = (counts: Parameters<typeof overview>[0], selected: ExecutionQueueStateCount['state'] | '' = '') =>
    renderToStaticMarkup(createElement(QueueStateStrip, { overview: overview(counts), selected, onSelect: noop, onSelectGroup: noop }));

  it('is not drawn beside the group\'s own press, so «Ошибки 9» does not stand by «Ошибка 9»', () => {
    const markup = strip({ failed: 9, succeeded: 2 });
    expect(markup).toContain('Ошибки 9');
    expect(markup).not.toContain('data-queue-state-chip="failed"');
    expect(markup).not.toContain('Ошибка 9');
    expect(markup).not.toContain('data-queue-state-chip="succeeded"');
  });

  it('is drawn when the group holds two states with a job, each with its own count', () => {
    const markup = strip({ failed: 7, dead_letter: 2 });
    expect(markup).toContain('Ошибки 9');
    expect(markup).toContain('data-queue-state-chip="failed"');
    expect(markup).toContain('data-queue-state-chip="dead_letter"');
  });

  it('is drawn when it is the state the list is narrowed to, so a filter shows what it is', () => {
    const markup = strip({ failed: 9 }, 'failed');
    expect(markup).toMatch(/aria-pressed="true"[^>]*data-queue-state-chip="failed"/);
  });
});

describe('the confirmations name the work', () => {
  const item: ExecutionQueueItem = {
    job_id: 'job_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', run_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', state: 'queued', priority: 0,
    created_at: '2026-10-09T10:00:00Z', available_at: '2026-10-09T10:00:00Z', ...QUEUE_WORK,
  };

  it('says the document and the version in each of the row\'s confirmations, and no run\'s number', () => {
    const labels = [
      intentLabel({ kind: 'cancel', item, key: 'ik' }),
      intentLabel({ kind: 'reaudit', item, key: 'ik' }),
      intentLabel({ kind: 'priority', item, priority: 7, key: 'ik' }),
    ];
    expect(labels[0]).toBe('Отменить прогон документа «АР, лист 3», версия 2?');
    expect(labels[1]).toBe('Начать повторный аудит документа «АР, лист 3», версия 2?');
    expect(labels[2]).toBe('Установить приоритет 7 для документа «АР, лист 3», версия 2?');
    for (const label of labels) {
      expect(label).not.toContain('run_');
      expect(label).not.toContain(item.run_id);
    }
  });
});
