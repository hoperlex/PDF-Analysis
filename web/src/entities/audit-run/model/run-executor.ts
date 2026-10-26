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
 */

import type { RunStatus } from '@/shared/api';

export interface RunExecutorLine {
  readonly name: string;
  /** The pinned model, or `null` when the reading carries none. */
  readonly model: string | null;
  /** The run is in the queue, so it is waiting for this executor. */
  readonly waiting: boolean;
}

const isText = (value: unknown): value is string => typeof value === 'string' && value.trim() !== '';

/** The executor of a run, or `null` when the run has none to show. */
export function runExecutorLine(run: Pick<RunStatus, 'executor' | 'state'>): RunExecutorLine | null {
  const executor = run.executor;
  if (executor === undefined || executor === null || !isText(executor.display_name)) return null;
  return {
    name: executor.display_name,
    model: isText(executor.pin_id) ? executor.pin_id : null,
    waiting: run.state === 'queued',
  };
}

const modelPart = (line: RunExecutorLine): string => (line.model === null ? '' : `, модель «${line.model}»`);

/** «Исполнитель «Основной шлюз», модель «…»» — or, in the queue, «Ждёт исполнителя «…»…». */
export function runExecutorSentence(line: RunExecutorLine): string {
  return line.waiting
    ? `Ждёт исполнителя «${line.name}»${modelPart(line)}`
    : `Исполнитель «${line.name}»${modelPart(line)}`;
}

/** The value of an «Исполнитель» row: «Основной шлюз», модель «…». */
export function runExecutorValue(line: RunExecutorLine): string {
  return `«${line.name}»${modelPart(line)}`;
}

/** «Ждёт исполнителя «…».» for a run in the queue; `null` for any other state. */
export function runWaitingSentence(line: RunExecutorLine): string | null {
  return line.waiting ? `Ждёт исполнителя «${line.name}».` : null;
}
