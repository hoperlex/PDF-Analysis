/**
 * M-17 (ruling `R-151t`, Q-MD-17): the overview tiles over «Процессы», as the original's. Servers online of all listed;
 * free slots over the online servers only, a `stale` server not online; the queue's running and waiting jobs.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { ExecutionWorker } from '@/shared/api';
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
