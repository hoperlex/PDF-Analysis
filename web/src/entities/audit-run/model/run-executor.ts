/**
 * The executor a run is on, in words (`EXEC-PAR-WEB-01`, over `RunStatus.executor`).
 *
 * `RunStatus.executor` is the connection the run froze at start, the name an administrator gave
 * it and the model its frozen settings pin — and nothing else: no kind, address, key or probe.
 * A run that froze no connection (every run on the environment source) carries no such member,
 * and the contract allows `null` as well; for both the answer here is `null`, and a screen draws
 * nothing — no line, no placeholder, no «не указан». A member whose name is empty or is not text
 * is treated the same way: a screen that cannot say which executor does not say one.
 *
 * A run in the queue says which executor it is waiting for. The queue holds a run back for a free
 * worker as well as for a busy executor, and the reading does not say which, so the sentence names
 * the executor the run is waiting to run on and claims no more.
 *
 * `EXEC2-WEB-CAP-01`: when the reading does say which (`RunStatus.queue_reason`), the sentence says
 * it in the words of `QUEUE_REASON_LABELS` — «В очереди: исполнитель занят», «В очереди: раннер не
 * в сети» — and a run whose reading has no reason keeps the sentence above, word for word.
 */

import type { RunQueueReason, RunStatus } from '@/shared/api';

import { QUEUE_REASON_LABELS, runQueueReason } from './run-queue-reason';

export interface RunExecutorLine {
  readonly name: string;
  /** The pinned model, or `null` when the reading carries none. */
  readonly model: string | null;
  /** The run is in the queue, so it is waiting for this executor. */
  readonly waiting: boolean;
  /** Why it is waiting, when the reading says; present only on a waiting line. */
  readonly queueReason?: RunQueueReason;
}

const isText = (value: unknown): value is string => typeof value === 'string' && value.trim() !== '';

/** The executor of a run, or `null` when the run has none to show. */
export function runExecutorLine(run: Pick<RunStatus, 'executor' | 'state' | 'queue_reason'>): RunExecutorLine | null {
  const executor = run.executor;
  if (executor === undefined || executor === null || !isText(executor.display_name)) return null;
  const reason = runQueueReason(run);
  return {
    name: executor.display_name,
    model: isText(executor.pin_id) ? executor.pin_id : null,
    waiting: run.state === 'queued',
    ...(reason === null ? {} : { queueReason: reason }),
  };
}

const modelPart = (line: RunExecutorLine): string => (line.model === null ? '' : `, модель «${line.model}»`);

/**
 * «Исполнитель «Основной шлюз», модель «…»» — or, in the queue, «Ждёт исполнителя «…»…», and with a
 * reason «В очереди: исполнитель занят — «Основной шлюз», модель «…»».
 */
export function runExecutorSentence(line: RunExecutorLine): string {
  if (line.waiting && line.queueReason !== undefined) {
    return `${QUEUE_REASON_LABELS[line.queueReason]} — «${line.name}»${modelPart(line)}`;
  }
  return line.waiting
    ? `Ждёт исполнителя «${line.name}»${modelPart(line)}`
    : `Исполнитель «${line.name}»${modelPart(line)}`;
}

/** The value of an «Исполнитель» row: «Основной шлюз», модель «…». */
export function runExecutorValue(line: RunExecutorLine): string {
  return `«${line.name}»${modelPart(line)}`;
}

/**
 * «Ждёт исполнителя «…».» for a run in the queue, «В очереди: исполнитель занят.» when the reading
 * says why (the executor is named beside it by the page's «Исполнитель» row); `null` for any other
 * state.
 */
export function runWaitingSentence(line: RunExecutorLine): string | null {
  if (!line.waiting) return null;
  return line.queueReason === undefined
    ? `Ждёт исполнителя «${line.name}».`
    : `${QUEUE_REASON_LABELS[line.queueReason]}.`;
}
