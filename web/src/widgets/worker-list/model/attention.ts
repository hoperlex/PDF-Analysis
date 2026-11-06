/**
 * What «Обзор» of «Исполнители» puts under «Требует внимания», as the original's overview does: the servers that have
 * gone quiet and the jobs that ended badly. Only what the first pages of the registry and of the queue say -- the screen
 * says so itself -- and only two kinds, because the rest cannot be told from the data:
 *
 *   - a worker whose state is `stale` (it missed its heartbeat but is not yet `offline`), where a long-gone `offline` row
 *     is history, not news;
 *   - a job whose state is `failed` or `dead_letter`.
 *
 * Pure: the server's order is kept inside each kind, workers first.
 */

import type { ExecutionQueueItem, ExecutionWorker } from '@/shared/api';

export type AttentionItem =
  | { readonly kind: 'worker'; readonly worker: ExecutionWorker }
  | { readonly kind: 'job'; readonly item: ExecutionQueueItem };

export function attentionItems(
  workers: readonly ExecutionWorker[],
  jobs: readonly ExecutionQueueItem[],
): readonly AttentionItem[] {
  return [
    ...workers.filter((worker) => worker.state === 'stale').map((worker): AttentionItem => ({ kind: 'worker', worker })),
    ...jobs.filter((item) => item.state === 'failed' || item.state === 'dead_letter')
      .map((item): AttentionItem => ({ kind: 'job', item })),
  ];
}

/** The jobs waiting their turn, the nearest first: the original's «Ближайшие проверки». */
export function nextJobs(jobs: readonly ExecutionQueueItem[], limit: number): readonly ExecutionQueueItem[] {
  return jobs
    .filter((item) => item.state === 'queued' || item.state === 'retry_wait')
    .sort((a, b) => (a.queue_position ?? Number.MAX_SAFE_INTEGER) - (b.queue_position ?? Number.MAX_SAFE_INTEGER))
    .slice(0, limit);
}
