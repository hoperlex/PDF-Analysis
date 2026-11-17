/**
 * `UIP-S13-02`: the queue's «N / M» and its «✓ N ✗ M», as the original's queue says them over its row of counts. Pure arithmetic over
 * the page's `overview` (the server's count of every state over the period), nothing read from the rows in view: the figures are
 * those of the whole queue, not of the page.
 *
 * **M** is every job of the period, **N** the ones that have ended (done, cancelled, failed, or stopped after their retries), **✓** the
 * ones that ended well and **✗** the ones that ended in failure. A job that was cancelled has ended and is neither: the two marks do not
 * have to add up to N, and the line does not pretend that they do.
 */

import type { ExecutionQueueStateCount } from '@/shared/api';
import { QUEUE_STATE_GROUPS } from '@/entities/execution';
import type { ExecutionQueueState } from '@/entities/execution';

export interface QueueProgress {
  /** Every job the overview counts: the M of «N / M». */
  readonly total: number;
  /** The jobs that have ended, in any way: the N of «N / M». */
  readonly ended: number;
  /** Of them, the ones that ended well. */
  readonly succeeded: number;
  /** Of them, the ones that ended in failure (the group «Ошибки»). */
  readonly failed: number;
}

const ENDED: ReadonlySet<ExecutionQueueState> = new Set(
  QUEUE_STATE_GROUPS.filter((group) => group.key !== 'active').flatMap((group) => group.states),
);
const FAILED: ReadonlySet<ExecutionQueueState> = new Set(
  QUEUE_STATE_GROUPS.filter((group) => group.key === 'errors').flatMap((group) => group.states),
);

/** The figures of the line, or `null` when the page carries no overview or the queue holds no job (nothing to count, nothing drawn). */
export function queueProgress(overview: readonly ExecutionQueueStateCount[] | undefined): QueueProgress | null {
  if (overview === undefined) return null;
  let total = 0;
  let ended = 0;
  let succeeded = 0;
  let failed = 0;
  for (const entry of overview) {
    total += entry.count;
    if (ENDED.has(entry.state)) ended += entry.count;
    if (entry.state === 'succeeded') succeeded += entry.count;
    if (FAILED.has(entry.state)) failed += entry.count;
  }
  return total === 0 ? null : { total, ended, succeeded, failed };
}
