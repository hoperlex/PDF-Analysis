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
 *
 * `EXEC2-WEB-GROUPS-01` (ADR-0026 decisions 12 to 15): a run admitted by a rule or a group has a
 * `binding_state`, and the two phases are never worded alike.
 *
 * - `pending`: admission froze the group, the rule and the **planned** model (`RunStatus.planned`);
 *   no connection is chosen and no model has been called. The line says «плановая модель» and that
 *   the connection is chosen when the work is sent. It never names a connection and never says a
 *   model ran, answered or was used, and it carries the stored `wait_reason` and `waiting_since`.
 * - `bound`: dispatch chose a member and wrote the binding (`RunStatus.binding`) once. The line says
 *   «фактическая модель» and the connection it was bound to, from the binding and nowhere else.
 *
 * Every other run (`frozen_at_start`, or no `binding_state`: every run that existed before groups) is
 * worded exactly as before.
 */

import type { RunQueueReason, RunStatus } from '@/shared/api';
import { formatInstant } from '@/shared/lib';

import { QUEUE_REASON_LABELS, runQueueReason } from './run-queue-reason';

export interface RunExecutorLine {
  /** The connection's name; empty while only the plan is known (`phase` `planned`). */
  readonly name: string;
  /** The pinned model, or `null` when the reading carries none. */
  readonly model: string | null;
  /** The run is in the queue, so it is waiting for this executor. */
  readonly waiting: boolean;
  /** Why it is waiting, when the reading says; present only on a waiting line. */
  readonly queueReason?: RunQueueReason;
  /**
   * Present only for a run admitted by a rule or a group. `planned`: the model is the plan and no
   * connection is chosen. `bound`: the name and the model are the connection dispatch chose.
   */
  readonly phase?: 'planned' | 'bound';
  /** When the run began waiting for the reason in `queueReason` (`planned` lines only). */
  readonly waitingSince?: string;
}

type RunExecutorSource = Pick<
  RunStatus,
  'executor' | 'state' | 'queue_reason' | 'wait_reason' | 'binding_state' | 'binding' | 'planned' | 'waiting_since'
>;

const isText = (value: unknown): value is string => typeof value === 'string' && value.trim() !== '';

/** The executor of a run, or `null` when the run has none to show. */
export function runExecutorLine(run: RunExecutorSource): RunExecutorLine | null {
  const reason = runQueueReason(run);
  const waiting = run.state === 'queued';

  if (run.binding_state === 'pending') {
    const planned = run.planned;
    return {
      name: '',
      model: planned !== undefined && isText(planned.pin_id) ? planned.pin_id : null,
      waiting,
      phase: 'planned',
      ...(reason === null ? {} : { queueReason: reason }),
      ...(run.waiting_since === undefined ? {} : { waitingSince: run.waiting_since }),
    };
  }

  const binding = run.binding;
  if (run.binding_state === 'bound' && binding !== undefined && isText(binding.display_name)) {
    return {
      name: binding.display_name,
      model: isText(binding.pin_id) ? binding.pin_id : null,
      waiting,
      phase: 'bound',
      ...(reason === null ? {} : { queueReason: reason }),
    };
  }

  const executor = run.executor;
  if (executor === undefined || executor === null || !isText(executor.display_name)) return null;
  return {
    name: executor.display_name,
    model: isText(executor.pin_id) ? executor.pin_id : null,
    waiting,
    ...(reason === null ? {} : { queueReason: reason }),
  };
}

const modelPart = (line: RunExecutorLine): string => (line.model === null ? '' : `, модель «${line.model}»`);

const lowerFirst = (text: string): string => `${text.charAt(0).toLowerCase()}${text.slice(1)}`;

/** What a run on a group says before dispatch: the plan, and that the connection is not chosen yet. */
const PLANNED_TAIL = 'подключение будет выбрано при отправке в работу';

/** «Плановая модель «…», подключение будет выбрано при отправке в работу» — the plan, never a fact. */
function plannedValue(line: RunExecutorLine): string {
  return line.model === null
    ? `Плановая модель не указана, ${PLANNED_TAIL}`
    : `Плановая модель «${line.model}», ${PLANNED_TAIL}`;
}

/** «Фактическая модель «…», подключение «…»» — what dispatch bound the run to, from the binding. */
function boundValue(line: RunExecutorLine): string {
  return line.model === null
    ? `Фактическое подключение «${line.name}»`
    : `Фактическая модель «${line.model}», подключение «${line.name}»`;
}

/**
 * «Исполнитель «Основной шлюз», модель «…»» — or, in the queue, «Ждёт исполнителя «…»…», and with a
 * reason «В очереди: исполнитель занят — «Основной шлюз», модель «…»».
 *
 * A run on a group says «Плановая модель «…», подключение будет выбрано при отправке в работу» before
 * dispatch and «Фактическая модель «…», подключение «…»» after it, with the reason in front while it
 * waits.
 */
export function runExecutorSentence(line: RunExecutorLine): string {
  if (line.phase === 'planned') {
    const body = plannedValue(line);
    if (!line.waiting) return body;
    const head = line.queueReason === undefined ? 'Ждёт отправки в работу' : QUEUE_REASON_LABELS[line.queueReason];
    return `${head} — ${lowerFirst(body)}`;
  }
  if (line.phase === 'bound') {
    const body = boundValue(line);
    if (!line.waiting || line.queueReason === undefined) return body;
    return `${QUEUE_REASON_LABELS[line.queueReason]} — ${lowerFirst(body)}`;
  }
  if (line.waiting && line.queueReason !== undefined) {
    return `${QUEUE_REASON_LABELS[line.queueReason]} — «${line.name}»${modelPart(line)}`;
  }
  return line.waiting
    ? `Ждёт исполнителя «${line.name}»${modelPart(line)}`
    : `Исполнитель «${line.name}»${modelPart(line)}`;
}

/**
 * The value of an «Исполнитель» row: «Основной шлюз», модель «…». For a run on a group, the plan
 * before dispatch and the binding after it, in the words of `runExecutorSentence`.
 */
export function runExecutorValue(line: RunExecutorLine): string {
  if (line.phase === 'planned') return plannedValue(line);
  if (line.phase === 'bound') return boundValue(line);
  return `«${line.name}»${modelPart(line)}`;
}

/**
 * «Ждёт исполнителя «…».» for a run in the queue, «В очереди: исполнитель занят.» when the reading
 * says why (the executor is named beside it by the page's «Исполнитель» row); `null` for any other
 * state.
 *
 * A run on a group that waits says why, or that the connection is not chosen yet, and — when the
 * reading carries it — since when.
 */
export function runWaitingSentence(line: RunExecutorLine): string | null {
  if (!line.waiting) return null;
  if (line.phase === 'planned') {
    const head = line.queueReason === undefined
      ? 'Ждёт отправки в работу: подключение группы ещё не выбрано.'
      : `${QUEUE_REASON_LABELS[line.queueReason]}.`;
    return line.waitingSince === undefined ? head : `${head} Ждёт с ${formatInstant(line.waitingSince)}.`;
  }
  return line.queueReason === undefined
    ? `Ждёт исполнителя «${line.name}».`
    : `${QUEUE_REASON_LABELS[line.queueReason]}.`;
}
