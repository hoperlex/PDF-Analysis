/**
 * «Убрать завершённые (N)» (`UIP-S13-03`): the original's button that clears the finished and the failed records from its list, as a
 * **view of this browser**. Nothing is deleted and nothing is written to the server (a hidden record is a record hidden from everyone
 * if it were; AGENTS §4): the rows are read as they were and the page does not draw the ones in a finished state while the view is on.
 *
 * «Finished» is the original's pair of words for the two groups that are not «Активные»: a job that ended well or was cancelled
 * (`Завершённые`) and one that ended in failure (`Ошибки`). N is the number of such rows **in the page in front of the reader**, which
 * is what the press would remove from the screen, and is not the queue's count over all its pages.
 */

import type { ExecutionQueueItem } from '@/shared/api';
import { QUEUE_STATE_GROUPS } from '@/entities/execution';

const FINISHED: ReadonlySet<string> = new Set(QUEUE_STATE_GROUPS.filter((group) => group.key !== 'active').flatMap((group) => group.states));

export function isFinished(state: string): boolean {
  return FINISHED.has(state);
}

/** The N of «Убрать завершённые (N)». */
export function finishedCount(items: readonly ExecutionQueueItem[]): number {
  return items.filter((item) => isFinished(item.state)).length;
}

/** The rows the view draws: all of them, or the ones that are not finished. */
export function visibleRows(items: readonly ExecutionQueueItem[], hideFinished: boolean): readonly ExecutionQueueItem[] {
  return hideFinished ? items.filter((item) => !isFinished(item.state)) : items;
}
