/**
 * M-17 (ruling `R-151t`, Q-MD-17): the overview tiles, as the original's. Servers online of all listed;
 * free slots over the online servers only, a `stale` server not online; the queue's running and waiting jobs.
 * UI-B-63, UI-B-64: they were the content of the first tab, «Обзор», with the queue's line and a link from each tile to
 * what it summarises. `HOSTS-WEB-01` (plan 2026-11-09 §7.1) replaced that tab with the summary line of «Серверы»; the tiles stay
 * a widget (`widgets/worker-list`) and this file holds them to what they say, on their own.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { ExecutionQueueStateCount, ExecutionWorker } from '@/shared/api';
import { workersOverview } from '@/entities/execution';
import { WorkersOverviewView } from '@/widgets/worker-list';

const worker = (state: ExecutionWorker['state'], slots: number, runs: number): ExecutionWorker => ({
  worker_id: `wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8${state.length}` as ExecutionWorker['worker_id'], state, intake_enabled: true, slots,
  version: '0.5.0', started_at: '2026-10-09T10:00:00Z', heartbeat_at: '2026-10-09T10:05:00Z',
  current_run_ids: Array.from({ length: runs }, (_, n) => `run_01J9ZQ8K7NHVXW3T2R5M6P4Q8${n}` as ExecutionWorker['current_run_ids'][number]),
});

describe('the workers overview', () => {
  it('counts free slots over the online servers only, as the owner ruled («2 / 4»)', () => {
    const overview = workersOverview([worker('online', 4, 2), worker('stale', 2, 0), worker('offline', 2, 0)], false);
    expect(overview).toEqual({ online: 1, total: 3, onlineSlots: 4, freeSlots: 2, partial: false });
  });

  it('says the servers not online and the queue, and nothing it cannot count', () => {
    const markup = renderToStaticMarkup(createElement(WorkersOverviewView, {
      workers: { online: 1, total: 3, onlineSlots: 4, freeSlots: 2, partial: false },
      queue: [{ state: 'queued', count: 3 }, { state: 'retry_wait', count: 1 }, { state: 'running', count: 1 }, { state: 'failed', count: 9 }],
    }));
    expect(markup).toContain('Серверы онлайн');
    expect(markup).toContain('1 / 3');
    expect(markup).toContain('2 не в сети');
    expect(markup).toContain('2 / 4');
    expect(markup).toMatch(/В очереди<\/span><span[^>]*>4</);
    expect(markup).not.toContain('Ошибки');
    expect(markup).not.toContain('Завершено сегодня');
  });
});

const OVERVIEW: readonly ExecutionQueueStateCount[] = [
  { state: 'queued', count: 3 }, { state: 'leased', count: 0 }, { state: 'running', count: 1 },
  { state: 'retry_wait', count: 1 }, { state: 'succeeded', count: 12 }, { state: 'failed', count: 2 },
  { state: 'cancelled', count: 0 }, { state: 'dead_letter', count: 0 },
];
const FIGURES = { online: 1, total: 3, onlineSlots: 4, freeSlots: 2, partial: false } as const;
const view = (props: Partial<Parameters<typeof WorkersOverviewView>[0]>) =>
  renderToStaticMarkup(createElement(WorkersOverviewView, { workers: FIGURES, ...props }));

describe('the overview tiles lead to what they summarise', () => {
  it('links the two server tiles to «Процессы» and the two queue tiles to «Очередь»', () => {
    const markup = view({ queue: OVERVIEW, processesHref: '?tab=processes' });
    const tile = (name: string) => markup.match(new RegExp(`<li[^>]*data-workers-tile="${name}"[^>]*>.*?</li>`))?.[0] ?? '';
    for (const name of ['servers', 'slots']) {
      expect(tile(name)).toContain('data-workers-tile-link="processes"');
      expect(tile(name)).toContain('href="?tab=processes"');
      expect(tile(name)).not.toContain('data-workers-tile-link="queue"');
    }
    for (const name of ['running', 'queued']) {
      expect(tile(name)).toContain('data-workers-tile-link="queue"');
      expect(tile(name)).toContain('href="/queue"');
      expect(tile(name)).not.toContain('data-workers-tile-link="processes"');
    }
  });

  it('draws no link to a tab it was given no address for, and no queue tile it has no figures for', () => {
    const markup = view({});
    expect(markup).not.toContain('data-workers-tile-link');
    expect(markup).not.toContain('data-workers-tile="running"');
    expect(markup).not.toContain('data-workers-tile="queued"');
    expect(markup).not.toContain('data-workers-queue-overview');
  });

  it('says the queue by state in one line, as the queue does', () => {
    expect(view({ queue: OVERVIEW })).toContain(
      'data-workers-queue-overview="">Всего 19: Ожидает 3 · Выполняется 1 · Ожидает повтора 1 · Завершена 12 · Ошибка 2</p>',
    );
    expect(view({ queue: OVERVIEW.map((entry) => ({ ...entry, count: 0 })) })).toContain('data-workers-queue-overview="">Задач нет.</p>');
  });
});
