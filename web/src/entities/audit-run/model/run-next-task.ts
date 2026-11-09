/**
 * What a waiting run's card «Следующая задача» says (`UI-B-70`), from what the run page and the queue's first page already
 * read: the run's own `queue_reason` / `wait_reason`, and the queue's items, overview and pause flag.
 *
 * The original's card is the scheduler's recommendation: which project goes to which server. This installation's queue gives
 * no such recommendation (the dispatcher picks the next job inside and does not hand the choice out), so the card says only
 * what the data says: this run's place in the order, the job that goes first, why this one waits, what is in work and when
 * the nearest running job is estimated to finish. Nothing is guessed: a figure the reading does not carry is left out, and
 * the queue's first page is said to be a first page when it is.
 *
 * The queue's order is the dispatcher's own (`queue_position`: priority, then the oldest first, over the queued jobs of
 * the whole installation), so a position read from the first page is the run's position, not a position within the page.
 */

import type { ExecutionQueueItem, ExecutionQueuePage, RunQueueReason, RunStatus } from '@/shared/api';
import { formatInstant } from '@/shared/lib';

import { QUEUE_REASON_LABELS, runQueueReason } from './run-queue-reason';

export type RunNextTaskSource = Pick<RunStatus, 'run_id' | 'state' | 'queue_reason' | 'wait_reason' | 'waiting_since'>;

export interface RunNextTask {
  /** This run's place among the queued jobs; `null` when the queue was not read or does not list this run. */
  readonly position: number | null;
  /** How many queued jobs go before this run; `null` when `position` is. */
  readonly ahead: number | null;
  /** This run's job is the first of the queued jobs. */
  readonly isNext: boolean;
  /** The queued job that goes first, when it is not this run's; `null` otherwise or when none is listed. */
  readonly next: ExecutionQueueItem | null;
  /** Why this run waits, from its own reading. */
  readonly reason: RunQueueReason | null;
  /** When the run began waiting for that reason, when the reading says. */
  readonly waitingSince: string | null;
  /** The installation's queue is paused: no job is handed out. `null` when the queue was not read. */
  readonly paused: boolean | null;
  /** Jobs leased or running, from the queue's overview over all of it; `null` without an overview. */
  readonly inWork: number | null;
  /** Jobs queued, from the overview; `null` without one. */
  readonly queued: number | null;
  /** The running job with the nearest estimated finish, from the first page; `null` when none carries an estimate. */
  readonly finishing: (ExecutionQueueItem & { readonly estimated_finish_at: string }) | null;
  /** What was read of the queue: nothing, its first page of several, or all of it. */
  readonly read: 'none' | 'partial' | 'whole';
}

function count(page: ExecutionQueuePage | undefined, states: readonly string[]): number | null {
  const overview = page?.overview;
  if (overview === undefined) return null;
  return overview.filter((entry) => states.includes(entry.state)).reduce((sum, entry) => sum + entry.count, 0);
}

export function runNextTask(run: RunNextTaskSource, page: ExecutionQueuePage | undefined): RunNextTask {
  const items = page?.items ?? [];
  const queuedItems = items
    .filter((item) => item.state === 'queued' && item.queue_position !== undefined)
    .sort((a, b) => (a.queue_position ?? 0) - (b.queue_position ?? 0));
  const mine = queuedItems.find((item) => item.run_id === run.run_id);
  const position = mine?.queue_position ?? null;
  const first = queuedItems[0];
  const isNext = position !== null && position === first?.queue_position;
  const finishing = items
    .flatMap((item) => (item.state === 'running' && item.estimated_finish_at !== undefined && !Number.isNaN(Date.parse(item.estimated_finish_at))
      ? [item as ExecutionQueueItem & { estimated_finish_at: string }] : []))
    .sort((a, b) => Date.parse(a.estimated_finish_at) - Date.parse(b.estimated_finish_at))[0] ?? null;
  return {
    position,
    ahead: position === null ? null : position - 1,
    isNext,
    next: first === undefined || isNext || first.run_id === run.run_id ? null : first,
    reason: runQueueReason(run),
    waitingSince: run.waiting_since ?? null,
    paused: page === undefined ? null : page.paused,
    inWork: count(page, ['leased', 'running']),
    queued: count(page, ['queued']),
    finishing,
    read: page === undefined ? 'none' : page.page.next_cursor === null ? 'whole' : 'partial',
  };
}

/** Where this run stands in the order, in one sentence; `null` when the queue was not read. */
export function nextTaskPlace(task: RunNextTask): string | null {
  if (task.read === 'none') return null;
  if (task.isNext) return 'Эта задача — первая в очереди: она уйдёт в работу следующей.';
  if (task.position !== null) return `№ ${task.position} в очереди. Впереди в очереди: ${task.ahead ?? 0}.`;
  return task.read === 'partial'
    ? 'Этой задачи нет на первой странице очереди: впереди неё больше задач, чем страница показывает.'
    : 'Этой задачи нет в очереди на момент чтения: она могла уйти в работу после последнего чтения.';
}

/** Why the run waits, as the sentences the data supports; a run the data does not explain says so. */
export function nextTaskWhy(task: RunNextTask): readonly string[] {
  const sentences: string[] = [];
  if (task.paused === true) sentences.push('Очередь на паузе: пока её не возобновят, ни одна задача не уходит в работу.');
  if (task.reason !== null) {
    sentences.push(task.waitingSince === null
      ? `${QUEUE_REASON_LABELS[task.reason]}.`
      : `${QUEUE_REASON_LABELS[task.reason]}. Ждёт с ${formatInstant(task.waitingSince)}.`);
  }
  if (task.ahead !== null && task.ahead > 0) sentences.push('Впереди стоят другие задачи: сначала уходят они.');
  return sentences.length > 0 ? sentences : ['Сервер не назвал причину ожидания.'];
}

/** What is in work now and when the nearest running job is estimated to finish; `null` when neither is known. */
export function nextTaskWork(task: RunNextTask): string | null {
  const parts: string[] = [];
  if (task.inWork !== null) parts.push(`в работе: ${task.inWork}`);
  if (task.queued !== null) parts.push(`ожидают: ${task.queued}`);
  if (task.finishing !== null) parts.push(`ближайшее завершение по оценке: ${formatInstant(task.finishing.estimated_finish_at)}`);
  if (parts.length === 0) return null;
  const line = parts.join(' · ');
  return `${line.charAt(0).toUpperCase()}${line.slice(1)}`;
}
