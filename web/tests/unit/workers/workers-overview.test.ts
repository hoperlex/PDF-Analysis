/**
 * M-17 (ruling `R-151t`, Q-MD-17): the overview tiles, as the original's. Servers online of all listed;
 * free slots over the online servers only, a `stale` server not online; the queue's running and waiting jobs.
 * UI-B-63, UI-B-64: they are the content of the first tab, «Обзор», with the queue's line and a link from each tile to
 * what it summarises.
 */

import { createElement } from 'react';
import type { ComponentType } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { ExecutionQueueStateCount, ExecutionWorker } from '@/shared/api';
import { ApiError, TransportError, queryKeys } from '@/shared/api';
import { WORKER_PAGE_LIMIT, workersOverview } from '@/entities/execution';
import { WorkersOverviewView } from '@/widgets/worker-list';
import { WorkersPage } from '@/_pages/workers';
import type { WorkersPageProps } from '@/_pages/workers';

import { newClient, renderScreen, seedError } from '../screens/harness';

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

describe('«Обзор», the first tab of «Исполнители»', () => {
  const RUNNING = ['wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8A', 'online', 4, 2] as const;
  function worker(id: string, state: ExecutionWorker['state'], slots: number, runs: number): ExecutionWorker {
    return {
      worker_id: id as ExecutionWorker['worker_id'], state, intake_enabled: true, slots, version: '0.5.0',
      started_at: '2026-10-09T10:00:00Z', heartbeat_at: '2026-10-09T10:05:00Z',
      current_run_ids: Array.from({ length: runs }, (_, n) => `run_01J9ZQ8K7NHVXW3T2R5M6P4Q8${n}` as ExecutionWorker['current_run_ids'][number]),
    };
  }
  const WORKERS = [
    worker(RUNNING[0], RUNNING[1], RUNNING[2], RUNNING[3]),
    worker('wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', 'stale', 2, 0),
    worker('wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8C', 'offline', 2, 0),
  ];

  function overviewPage(queue: 'seeded' | 'failed' | 'unread', registry: 'seeded' | 'failed' = 'seeded', props: WorkersPageProps = { initialTab: 'overview' }): string {
    const client = newClient();
    if (registry === 'seeded') {
      client.setQueryData(queryKeys.execution.workers(undefined, WORKER_PAGE_LIMIT), { items: WORKERS, page: { next_cursor: null } });
    } else {
      seedError(client, queryKeys.execution.workers(undefined, WORKER_PAGE_LIMIT), new TransportError('connection closed'));
    }
    if (queue === 'seeded') {
      client.setQueryData(queryKeys.execution.queue(undefined, {}), { items: [], page: { next_cursor: null }, paused: false, overview: OVERVIEW });
    } else if (queue === 'failed') {
      seedError(client, queryKeys.execution.queue(undefined, {}), new TransportError('connection closed'));
    }
    client.setQueryData(queryKeys.account.me(), { roles: ['expert'] });
    return renderScreen(client, createElement(WorkersPage as ComponentType<WorkersPageProps>, props));
  }

  it('opens when the address names it, draws the tiles and the queue line, and nothing of the other tabs', () => {
    const markup = overviewPage('seeded');
    expect(markup).toContain('data-workers-panel="overview"');
    expect(markup).toMatch(/aria-selected="true"[^>]*data-workers-tab="overview"|data-workers-tab="overview"[^>]*aria-selected="true"/);
    expect(markup).toContain('data-workers-overview');
    expect(markup).toContain('Серверы онлайн');
    expect(markup).toContain('1 / 3');
    expect(markup).toContain('2 не в сети');
    expect(markup).toContain('2 / 4');
    expect(markup).toMatch(/Выполняется<\/span><span[^>]*>1</);
    expect(markup).toMatch(/В очереди<\/span><span[^>]*>4</);
    expect(markup).toContain('Всего 19: Ожидает 3 · Выполняется 1 · Ожидает повтора 1 · Завершена 12 · Ошибка 2');
    expect(markup).toContain('data-update-state="fresh"');
    // The tile links: to the tab by its address (the click opens it without leaving the screen), to the queue by its route.
    expect(markup).toContain('href="?tab=processes"');
    expect(markup).toContain('href="/queue"');
    // Nothing of the process list, and no figure the API does not give.
    expect(markup).not.toContain('data-worker-list');
    expect(markup).not.toContain('Не брать новые');
    expect(markup).not.toContain('Завершено сегодня');
  });

  it('is no longer drawn over «Процессы», which keeps the list', () => {
    const markup = overviewPage('seeded', 'seeded', { initialTab: 'processes' });
    expect(markup).toContain('data-workers-panel="processes"');
    expect(markup).not.toContain('data-workers-overview');
    expect(markup).not.toContain('data-workers-queue-overview');
    expect(markup).toContain('wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8A');
  });

  it('keeps the servers on screen and says the queue was not read, with the way to retry', () => {
    const markup = overviewPage('failed');
    expect(markup).toContain('data-workers-overview');
    expect(markup).toContain('1 / 3');
    expect(markup).toContain('data-workers-queue-failure=');
    expect(markup).toContain('Очередь не прочитана');
    expect(markup).not.toContain('data-workers-tile="queued"');
    expect(markup).not.toContain('data-workers-queue-overview');
  });

  it('says the queue is being read, not that it is empty, until its first read settles', () => {
    const markup = overviewPage('unread');
    expect(markup).toContain('data-workers-overview');
    expect(markup).not.toContain('data-workers-tile="queued"');
    expect(markup).not.toContain('Задач нет.');
    expect(markup).not.toContain('data-workers-queue-failure');
  });

  it('says the registry was not read instead of showing tiles of nothing', () => {
    const markup = overviewPage('seeded', 'failed');
    expect(markup).toContain('data-workers-read-failure=');
    expect(markup).toContain('Исполнители не прочитаны');
    expect(markup).not.toContain('data-workers-overview');
  });

  it('keeps the queue refusal as the refusal it is', () => {
    const client = newClient();
    client.setQueryData(queryKeys.execution.workers(undefined, WORKER_PAGE_LIMIT), { items: WORKERS, page: { next_cursor: null } });
    seedError(client, queryKeys.execution.queue(undefined, {}), new ApiError(503, {
      contract_version: '1.39.0', error_code: 'dependency_unavailable',
      message: 'Безопасный отказ.', correlation_id: 'cid-queue-1', retryable: false,
    }, null));
    client.setQueryData(queryKeys.account.me(), { roles: ['expert'] });
    const markup = renderScreen(client, createElement(WorkersPage as ComponentType<WorkersPageProps>, { initialTab: 'overview' }));
    expect(markup).toContain('data-workers-queue-failure=');
    expect(markup).toContain('cid-queue-1');
  });
});
