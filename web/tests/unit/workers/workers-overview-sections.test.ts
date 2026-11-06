/**
 * The blocks under the tiles of «Обзор» (`UI-B-64`): the servers, the nearest queued jobs and what needs attention, drawn
 * from the first pages the tiles already read.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { ExecutionQueueItem, ExecutionWorker } from '@/shared/api';
import { WorkersOverviewSections, attentionItems, nextJobs } from '@/widgets/worker-list';

import { QUEUE_WORK } from '../execution/queue-work';

const at = '2026-10-09T10:00:00Z';
const worker = (id: string, state: ExecutionWorker['state'], runs = 0): ExecutionWorker => ({
  worker_id: `wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8${id}` as ExecutionWorker['worker_id'], state, intake_enabled: true, slots: 2,
  version: '0.5.0', started_at: at, heartbeat_at: at,
  current_run_ids: Array.from({ length: runs }, (_, n) => `run_01J9ZQ8K7NHVXW3T2R5M6P4Q8${n}` as ExecutionWorker['current_run_ids'][number]),
});
const job = (id: string, state: string, extra: Partial<ExecutionQueueItem> = {}): ExecutionQueueItem => ({
  job_id: `job_01J9ZQ8K7NHVXW3T2R5M6P4Q8${id}`, run_id: `run_01J9ZQ8K7NHVXW3T2R5M6P4Q8${id}`, state, priority: 0,
  created_at: at, available_at: at, ...QUEUE_WORK, ...extra,
} as ExecutionQueueItem);

describe('what needs attention', () => {
  it('names a silent server and a job that ended badly, and neither a gone server nor a good job', () => {
    const items = attentionItems(
      [worker('A', 'online'), worker('B', 'stale'), worker('C', 'offline')],
      [job('1', 'succeeded'), job('2', 'failed'), job('3', 'dead_letter'), job('4', 'queued')],
    );
    expect(items.map((entry) => entry.kind === 'worker' ? entry.worker.worker_id : entry.item.job_id)).toEqual([
      'wrk_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', 'job_01J9ZQ8K7NHVXW3T2R5M6P4Q82', 'job_01J9ZQ8K7NHVXW3T2R5M6P4Q83',
    ]);
  });

  it('takes the waiting jobs nearest first and no more than asked', () => {
    const jobs = [job('1', 'queued', { queue_position: 3 }), job('2', 'running'), job('3', 'queued', { queue_position: 1 }),
      job('4', 'retry_wait', { queue_position: 2 }), job('5', 'queued')];
    expect(nextJobs(jobs, 3).map((entry) => entry.job_id.slice(-1))).toEqual(['3', '4', '1']);
    expect(nextJobs(jobs, 10)).toHaveLength(4);
  });
});

describe('the blocks of «Обзор»', () => {
  const draw = (props: Partial<Parameters<typeof WorkersOverviewSections>[0]>) =>
    renderToStaticMarkup(createElement(WorkersOverviewSections, { workers: [], workersPartial: false, ...props }));

  it('lists the servers that answer with their slots and says nothing of the gone ones', () => {
    const markup = draw({ workers: [worker('A', 'online', 1), worker('C', 'offline')] });
    expect(markup).toContain('data-overview-node="online"');
    expect(markup).toContain('Слотов: 2 (занято 1)');
    expect(markup).not.toContain('data-overview-node="offline"');
  });

  it('says that nothing needs attention, and says it is a first page when the server has more', () => {
    const markup = draw({ workers: [worker('A', 'online')], workersPartial: true });
    expect(markup).toContain('✓ Проблем не обнаружено');
    expect(markup).toContain('По первой странице исполнителей.');
  });

  it('draws the nearest queued jobs with their place and a failed job with its reason and a way to its run', () => {
    const markup = draw({
      jobs: [job('1', 'queued', { queue_position: 1 }), job('2', 'failed', { error_code: 'analysis_failed' })],
      jobsPartial: true,
    });
    expect(markup).toContain('data-overview-next-job="1"');
    expect(markup).toContain('№ 1');
    expect(markup).toContain('data-overview-attention-job="failed"');
    expect(markup).toContain(`href="/projects/${QUEUE_WORK.project_uid}/runs/run_01J9ZQ8K7NHVXW3T2R5M6P4Q82"`);
    expect(markup).toContain('По первой странице очереди.');
    expect(markup).toContain('href="/queue"');
  });

  it('draws no queue block while the queue is not read', () => {
    expect(draw({})).not.toContain('data-overview-next');
  });
});
