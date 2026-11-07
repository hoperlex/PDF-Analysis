/**
 * Moving a queued job to another place in the queue (`UI-B-52`): the original lets an operator drag a waiting job; here a
 * move is the one command the queue already has — a job's priority — and nothing else.
 *
 * The dispatcher takes queued jobs by priority (higher first), then the oldest `created_at`, then `job_id`
 * (`ORDER BY priority DESC, created_at, job_id`). So a job's place is a function of its priority and its age, and to put it
 * between two neighbours the one thing that can change is its priority. This module is the pure half: given the queued rows
 * in view in the order shown and the place the reader meant, which priority puts the job there — or why none does.
 *
 * **It changes one job and never another.** If no priority of this job alone puts it in the slot (its two neighbours stand
 * at the same priority and the job is not between them by age, or the priority the slot needs is outside −100…100), the
 * move is refused and says so. It never invents a second command to shift the neighbours. **The server's answer is the
 * truth:** the arithmetic here is a proposal the screen sends once; the list is read again afterwards and shows where the job
 * stands.
 *
 * **Only what is in view is known.** On a page after the first, the job above the first row is on an earlier page; on a page
 * before the last, the job below the last row is on a later one. A slot at that edge would be decided by a neighbour this
 * screen does not hold, so it is refused too.
 */

import type { ExecutionQueueItem } from '@/shared/api';

export const PRIORITY_MIN = -100;
export const PRIORITY_MAX = 100;

export type ReorderRefusal = 'not_queued' | 'edge_above' | 'edge_below' | 'no_room';

export type ReorderPlan =
  /** Send this priority for the job. */
  | { readonly kind: 'set'; readonly priority: number }
  /** The slot is the job's own place already: nothing to send. */
  | { readonly kind: 'keep' }
  | { readonly kind: 'refused'; readonly reason: ReorderRefusal };

export interface ReorderEdges {
  /** True when nothing queued stands above the first row in view (the first page). */
  readonly top: boolean;
  /** True when nothing queued stands below the last row in view (the last page). */
  readonly bottom: boolean;
}

const REFUSALS: Readonly<Record<ReorderRefusal, string>> = {
  not_queued: 'Переставлять можно только ожидающие задачи.',
  edge_above: 'Выше этой строки стоят задачи с предыдущей страницы: поставить задачу на её край нельзя. Откройте предыдущую страницу.',
  edge_below: 'Ниже этой строки стоят задачи со следующей страницы: поставить задачу на её край нельзя. Откройте следующую страницу.',
  no_room:
    'Одним приоритетом эту перестановку не выразить: соседние задачи стоят на одном приоритете или нужный приоритет вне диапазона от −100 до 100. Другие задачи не менялись.',
};

/** The sentence that says why a move was not made. */
export function reorderRefusalText(reason: ReorderRefusal): string {
  return REFUSALS[reason];
}

function instantOf(item: ExecutionQueueItem): number {
  const value = Date.parse(item.created_at);
  return Number.isNaN(value) ? 0 : value;
}

/** True when `a` is taken before `b` among queued jobs: priority first, then the older, then the identity. */
export function takenBefore(a: ExecutionQueueItem, b: ExecutionQueueItem): boolean {
  if (a.priority !== b.priority) return a.priority > b.priority;
  const left = instantOf(a);
  const right = instantOf(b);
  if (left !== right) return left < right;
  return a.job_id < b.job_id;
}

/**
 * The priority that puts the job `jobId` into slot `toIndex` of the queued rows in view (`queued`, in the order shown):
 * after the row that now stands at `toIndex - 1` and before the one at `toIndex`, the job itself taken out. The nearest such
 * priority to the job's own is chosen, so a move changes it as little as it can.
 */
export function planReorder(
  queued: readonly ExecutionQueueItem[],
  jobId: string,
  toIndex: number,
  edges: ReorderEdges,
): ReorderPlan {
  const from = queued.findIndex((item) => item.job_id === jobId);
  const moving = queued[from];
  if (moving === undefined) return { kind: 'refused', reason: 'not_queued' };
  const target = Math.max(0, Math.min(queued.length - 1, toIndex));
  if (target === from) return { kind: 'keep' };
  const rest = queued.filter((item) => item.job_id !== jobId);
  const above = rest[target - 1];
  const below = rest[target];
  if (above === undefined && !edges.top) return { kind: 'refused', reason: 'edge_above' };
  if (below === undefined && !edges.bottom) return { kind: 'refused', reason: 'edge_below' };
  const fits = (priority: number): boolean => {
    const candidate: ExecutionQueueItem = { ...moving, priority };
    return (above === undefined || takenBefore(above, candidate)) && (below === undefined || takenBefore(candidate, below));
  };
  // The job's own priority already puts it there: the order shown is stale, or the slot is its own place.
  if (fits(moving.priority)) return { kind: 'keep' };
  let best: number | null = null;
  for (let priority = PRIORITY_MIN; priority <= PRIORITY_MAX; priority += 1) {
    if (!fits(priority)) continue;
    if (best === null || Math.abs(priority - moving.priority) < Math.abs(best - moving.priority)) best = priority;
  }
  return best === null ? { kind: 'refused', reason: 'no_room' } : { kind: 'set', priority: best };
}

/**
 * The slot a key asks for: Alt+↑ is one place up and Alt+↓ one place down among the queued rows in view, as the drag's
 * keyboard alternative. Any other key, or the arrow without Alt (which the page's own scrolling and the list's reading keep),
 * asks for nothing (`null`).
 */
export function keyboardTarget(
  queued: readonly ExecutionQueueItem[],
  jobId: string,
  key: string,
  altKey: boolean,
): number | null {
  if (!altKey || (key !== 'ArrowUp' && key !== 'ArrowDown')) return null;
  const at = queued.findIndex((item) => item.job_id === jobId);
  if (at < 0) return null;
  return at + (key === 'ArrowUp' ? -1 : 1);
}
