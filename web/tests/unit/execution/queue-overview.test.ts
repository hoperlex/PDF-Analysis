/**
 * `UI-PARITY-P0M` (contract 1.28.0): the rest of the queue's group A, as the original's queue line and numbered items.
 * The page's overview counts every state over the period; the filter's options carry those counts; a queued job says its
 * place in the dispatcher's order and every job its attempts.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { ExecutionQueueItem, ExecutionQueueStateCount } from '@/shared/api';
import { queueOverviewLine, queueStateCount } from '@/entities/execution';
import { ExecutionQueue } from '@/widgets/execution-queue';

import { QUEUE_WORK } from './queue-work';

const CREATED = '2026-10-09T10:00:00Z';
const noop = (): void => {};

const OVERVIEW: readonly ExecutionQueueStateCount[] = [
  { state: 'queued', count: 3 }, { state: 'leased', count: 0 }, { state: 'running', count: 1 },
  { state: 'retry_wait', count: 0 }, { state: 'succeeded', count: 12 }, { state: 'failed', count: 2 },
  { state: 'cancelled', count: 0 }, { state: 'dead_letter', count: 0 },
];

function rows(items: readonly ExecutionQueueItem[]): string {
  return renderToStaticMarkup(createElement(ExecutionQueue, {
    items, roles: [], asOf: Date.parse('2026-10-09T10:05:00Z'), busy: false, filtered: false,
    workerOf: () => ({ kind: 'pending' as const }), onCancel: noop, onReaudit: noop, onPriority: noop,
    onNext: null, onPrevious: null,
  }));
}

describe('the queue overview', () => {
  it('says the total and every state that has a job, in the queue order', () => {
    expect(queueOverviewLine(OVERVIEW)).toBe('Всего 18: Ожидает 3 · Выполняется 1 · Завершена 12 · Ошибка 2');
    expect(queueOverviewLine(OVERVIEW.map((entry) => ({ ...entry, count: 0 })))).toBe('Задач нет.');
    expect(queueOverviewLine(undefined)).toBeNull();
  });

  it('gives the filter each state count, 0 for a state without jobs, nothing without an overview', () => {
    expect(queueStateCount(OVERVIEW, 'succeeded')).toBe(12);
    expect(queueStateCount(OVERVIEW, 'cancelled')).toBe(0);
    expect(queueStateCount(undefined, 'queued')).toBeNull();
  });

  it('numbers a queued job and counts the attempts of every job', () => {
    const markup = rows([
      { job_id: 'job_01J9ZQ8K7NHVXW3T2R5M6P4Q8A', run_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8A', state: 'queued', priority: 0,
        created_at: CREATED, available_at: CREATED, queue_position: 2, attempt_count: 0, ...QUEUE_WORK },
      { job_id: 'job_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', run_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', state: 'failed', priority: 0,
        created_at: CREATED, available_at: CREATED, attempt_count: 3, ...QUEUE_WORK },
    ]);
    expect(markup).toContain('№ 2 в очереди');
    expect(markup).toContain('Попыток: 0');
    expect(markup).toContain('Попыток: 3');
    expect(markup.match(/data-queue-position=/g)).toHaveLength(1);
  });
});
