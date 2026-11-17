/**
 * What «Отменить очередь» does and says (`UIP-S13-04`), as pure functions: which jobs it cancels, what each refusal is called, and the
 * honest sum «Отменено N из M».
 *
 * There is no «cancel everything» command on the server and none is needed: the queue is cancelled the way a person would do it by
 * hand, **one command per run, each with a key of its own**, and the result is the sum of the separate answers. A refusal is said by
 * its name and nothing is rolled back (a run already cancelled stays cancelled); a command whose outcome is unknown is said to be
 * unknown, not counted either way. A run is never named by its number: the words say the document and its version (`Г12-B`).
 */

import type { ExecutionQueueItem, ExecutionQueuePage, ExecutionQueueStateCount } from '@/shared/api';
import { QUEUE_STATE_GROUPS, canCancel, executionFailure } from '@/entities/execution';
import type { ExecutionFailure } from '@/entities/execution';

/** The jobs of `items` a cancel can reach (waiting, leased, running, waiting to retry), each run once. */
export function cancellableJobs(items: readonly ExecutionQueueItem[]): readonly ExecutionQueueItem[] {
  const seen = new Set<string>();
  return items.filter((item) => {
    if (!canCancel(item) || seen.has(item.run_id)) return false;
    seen.add(item.run_id);
    return true;
  });
}

const ACTIVE: ReadonlySet<string> = new Set(QUEUE_STATE_GROUPS.filter((group) => group.key === 'active').flatMap((group) => group.states));

/**
 * The N of «Отменить очередь (N)»: the jobs of the overview that are not finished. `0` (no button) for a page with no overview: the button
 * is offered only for a number the server has said, never for a guess.
 */
export function cancellableCount(overview: readonly ExecutionQueueStateCount[] | undefined): number {
  return overview === undefined ? 0 : overview.filter((entry) => ACTIVE.has(entry.state)).reduce((sum, entry) => sum + entry.count, 0);
}

/** What one run's cancel came to. */
export type CancelOutcome =
  | { readonly kind: 'cancelled'; readonly item: ExecutionQueueItem }
  | { readonly kind: 'refused'; readonly item: ExecutionQueueItem; readonly reason: string }
  /** The command's outcome is not known (a dropped answer, a server fault): the run may or may not be cancelled. */
  | { readonly kind: 'unknown'; readonly item: ExecutionQueueItem; readonly reason: string }
  /** The reader stopped the sweep before this run's turn: nothing was sent for it. */
  | { readonly kind: 'skipped'; readonly item: ExecutionQueueItem };

/** The words of a refusal, for the run it names. The state refusal is the one the single cancel gives: the run is past where a cancel can reach. */
export function cancelRefusal(failure: ExecutionFailure): string {
  switch (failure.kind) {
    case 'transition': return 'отмена на этапе проверки недоступна';
    case 'permission': return 'нет прав на отмену';
    case 'authentication': return 'нужно войти заново';
    case 'conflict': return 'состояние задачи изменилось, отмена не принята';
    case 'unknown_outcome': return 'исход неизвестен';
    default: return failure.detail;
  }
}

/** The document and the version of a job, as every sentence of the sweep names it. */
export function workName(item: Pick<ExecutionQueueItem, 'document_name' | 'version_ordinal'>): string {
  return `«${item.document_name}», версия ${item.version_ordinal}`;
}

export interface CancelSummary {
  /** The N of «Отменено N из M». */
  readonly cancelled: number;
  /** The M: every run the sweep was asked to cancel. */
  readonly total: number;
  readonly sentence: string;
  /** The runs that are not cancelled, each with its reason. */
  readonly rest: readonly { readonly item: ExecutionQueueItem; readonly reason: string }[];
}

export function cancelSummary(outcomes: readonly CancelOutcome[]): CancelSummary {
  const cancelled = outcomes.filter((outcome) => outcome.kind === 'cancelled').length;
  const rest = outcomes.flatMap((outcome) => {
    if (outcome.kind === 'cancelled') return [];
    return [{ item: outcome.item, reason: outcome.kind === 'skipped' ? 'отмена не отправлена: очередь остановлена' : outcome.reason }];
  });
  return { cancelled, total: outcomes.length, sentence: `Отменено ${cancelled} из ${outcomes.length}.`, rest };
}

/**
 * Every job of the group «Активные», page after page under the cursor each page names, read through `readPage` (the page's cached read
 * of `listExecutionQueue` with `state_group=active`). A cursor named twice is a fault of the listing and ends the read with an error: no part
 * of the queue is offered as the whole.
 */
export async function readActiveJobs(
  readPage: (cursor: string | undefined) => Promise<ExecutionQueuePage>,
): Promise<readonly ExecutionQueueItem[]> {
  const items: ExecutionQueueItem[] = [];
  const seen = new Set<string>();
  let cursor: string | undefined;
  for (;;) {
    const page = await readPage(cursor);
    items.push(...page.items);
    const next = page.page.next_cursor;
    if (next === null) return items;
    if (seen.has(next)) throw new Error('The queue named one cursor twice.');
    seen.add(next);
    cursor = next;
  }
}

export interface SweepOptions {
  /** The keys the sweep has given its runs, by job; a run sent again goes under the key it had. Filled in as runs are sent. */
  readonly keys: Map<string, string>;
  readonly newKey: () => string;
  /** The reader stopped the sweep: the runs not yet sent are not sent. Asked before each run. */
  readonly stopped: () => boolean;
  /** Called before each send with the number of runs sent so far. */
  readonly onProgress?: (sent: number, total: number) => void;
}

/**
 * Cancels `jobs` one after another, each by its own command (`cancel`) under its own key, and returns what each came to. A command that
 * throws is that run's outcome (refused, or unknown), never the sweep's: the next run is still sent. Nothing is sent in parallel and
 * nothing is rolled back.
 */
export async function sweepCancel(
  jobs: readonly ExecutionQueueItem[],
  cancel: (item: ExecutionQueueItem, key: string) => Promise<unknown>,
  options: SweepOptions,
): Promise<readonly CancelOutcome[]> {
  const outcomes: CancelOutcome[] = [];
  let sent = 0;
  for (const item of jobs) {
    if (options.stopped()) {
      outcomes.push({ kind: 'skipped', item });
      continue;
    }
    options.onProgress?.(sent, jobs.length);
    const key = options.keys.get(item.job_id) ?? options.newKey();
    options.keys.set(item.job_id, key);
    try {
      await cancel(item, key);
      outcomes.push({ kind: 'cancelled', item });
    } catch (error) {
      const failure = executionFailure(error, true);
      outcomes.push({ kind: failure.kind === 'unknown_outcome' ? 'unknown' : 'refused', item, reason: cancelRefusal(failure) });
    }
    sent += 1;
  }
  return outcomes;
}
