/**
 * The executor a comparison AI job is on, in words (`EXEC2-FOLLOWUP-01`, over `ComparisonAiJob.binding_state`, `planned`,
 * `binding`, `wait_reason` and `waiting_since`, ADR-0026 decisions 12 to 16).
 *
 * A job admitted by a rule or a group has a `binding_state`, and the two phases are never worded alike — the rule
 * `EXEC2-WEB-GROUPS-01` set for a Run (`entities/audit-run/model/run-executor.ts`), whose wording this module shares:
 *
 * - `pending`: admission froze the group, the rule and the **planned** model (`planned`); no connection is chosen and no model has
 *   been called. The line says «плановая модель» and that the connection is chosen at the job's first call to the model. It never
 *   names a connection and never says a model ran, answered or was used. While the job waits it carries the stored `wait_reason`
 *   and `waiting_since`: «Ждёт исполнителя: раннер не в сети. Ждёт с …».
 * - `bound`: the job's first call chose a member and wrote the binding (`binding`) once, for good — a retry or a resume stays on it.
 *   The line says «фактическая модель» and the connection it was bound to, from the binding and nowhere else.
 * - `unbound`: a `pending` job that has **ended** (failed, cancelled, completed) never got a connection and never will. Its line is the
 *   plan in the past tense — «подключение так и не было выбрано» — and never the future of «будет выбрано».
 *
 * Every other job (`frozen_at_start`, or no `binding_state`: each job that existed before groups) has no such line, and its screens
 * draw exactly what they drew.
 *
 * A job waits while it is queued, running or paused (a pause keeps the wait: `needs_reconsent` is exactly a paused job's wait); an
 * ended job waits for nothing, so a stale reason on one is not read. A reason this screen has no word for is not read either.
 */

import type { ComparisonAiJob, RunQueueReason } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import { boundExecutorValue, knownQueueReason, plannedExecutorValue } from '@/entities/audit-run';

export interface JobExecutorLine {
  /**
   * `planned`: the model is the plan and no connection is chosen yet. `bound`: the name and the model are the connection the job is on.
   * `unbound`: the job ended before it was given a connection.
   */
  readonly phase: 'planned' | 'bound' | 'unbound';
  /** The connection's name; empty while only the plan is known. */
  readonly name: string;
  /** The pinned model, or `null` when the reading carries none. */
  readonly model: string | null;
  /** The group the job was admitted on (`planned` lines only): what the capacity of the wait is read for. */
  readonly groupId?: string;
  /** The revision of that group the job froze (`planned.executor_group_revision_id`): the one it waits on, which may not be the current. */
  readonly groupRevisionId?: string;
  /**
   * The wait is counting down to its end: the job is queued or running. A paused job keeps its wait but is not counting, so no promise that
   * it ends is made of it. Present on `planned` lines.
   */
  readonly counting?: boolean;
  /** Why the job waits for an executor, when the reading says and this screen knows the word; `planned` lines only. */
  readonly waitReason?: RunQueueReason;
  /** When it began waiting for that reason. */
  readonly waitingSince?: string;
}

export type JobExecutorSource = Pick<ComparisonAiJob, 'state' | 'binding_state' | 'planned' | 'binding' | 'wait_reason' | 'waiting_since'>;

const isText = (value: unknown): value is string => typeof value === 'string' && value.trim() !== '';

/** A job that has ended waits for no executor. */
const WAITING_STATES: ReadonlySet<string> = new Set(['queued', 'running', 'paused']);
/** A wait counts down to its end only while the job is queued or running. */
const COUNTING_STATES: ReadonlySet<string> = new Set(['queued', 'running']);

/** The words of each reason a job waits for an executor (a `Record` over the contract's own set). */
export const JOB_WAIT_LABELS: Readonly<Record<RunQueueReason, string>> = {
  executor_at_capacity: 'Ждёт исполнителя: все места заняты',
  runner_offline: 'Ждёт исполнителя: раннер не в сети',
  needs_reconsent: 'Нужно новое согласие на стоимость',
  model_unavailable: 'Ждёт модель: на серверах её сейчас нет',
};

/** A job's connection is chosen at its first call to the model — not when work is sent, as a Run's is. */
export const JOB_PLANNED_TAIL = 'подключение будет выбрано при первом обращении к модели';
/** A job that ended before its first call was never given one: said in the past tense. */
export const JOB_UNBOUND_TAIL = 'подключение так и не было выбрано';

/** The executor of a job, or `null` when the job has none to show (it existed before groups, or it is not admitted by a group). */
export function jobExecutorLine(job: JobExecutorSource): JobExecutorLine | null {
  if (job.binding_state === 'pending') {
    const planned = job.planned;
    const model = planned !== undefined && isText(planned.pin_id) ? planned.pin_id : null;
    if (!WAITING_STATES.has(job.state)) return { phase: 'unbound', name: '', model };
    const reason = knownQueueReason(job.wait_reason);
    return {
      phase: 'planned',
      name: '',
      model,
      counting: COUNTING_STATES.has(job.state),
      ...(planned !== undefined && isText(planned.executor_group_id) ? { groupId: planned.executor_group_id } : {}),
      ...(planned !== undefined && isText(planned.executor_group_revision_id)
        ? { groupRevisionId: planned.executor_group_revision_id }
        : {}),
      ...(reason === null ? {} : { waitReason: reason }),
      ...(reason === null || job.waiting_since === undefined ? {} : { waitingSince: job.waiting_since }),
    };
  }
  const binding = job.binding;
  if (job.binding_state === 'bound' && binding !== undefined && isText(binding.display_name)) {
    return { phase: 'bound', name: binding.display_name, model: isText(binding.pin_id) ? binding.pin_id : null };
  }
  return null;
}

/**
 * «Плановая модель «…», подключение будет выбрано при первом обращении к модели» before the job's first call,
 * «Фактическая модель «…», подключение «…»» after it, and «Плановая модель «…», подключение так и не было выбрано» for a job that ended without
 * one — the plan, then the fact, never one in the other's words, and never a future for a job that has no future.
 */
export function jobExecutorSentence(line: JobExecutorLine): string {
  if (line.phase === 'planned') return plannedExecutorValue(line.model, JOB_PLANNED_TAIL);
  if (line.phase === 'unbound') return plannedExecutorValue(line.model, JOB_UNBOUND_TAIL);
  return boundExecutorValue(line.name, line.model);
}

/**
 * Why a job on a group waits, and since when: «Ждёт исполнителя: раннер не в сети. Ждёт с 2026-11-03 09:30:00 UTC.» Only a `planned`
 * line waits; `null` for a job that is bound or that waits for nothing.
 */
export function jobWaitSentence(line: JobExecutorLine): string | null {
  if (line.phase !== 'planned' || line.waitReason === undefined) return null;
  const head = `${JOB_WAIT_LABELS[line.waitReason]}.`;
  return line.waitingSince === undefined ? head : `${head} Ждёт с ${formatInstant(line.waitingSince)}.`;
}

/** The sentence a compact place (a cell's hint) carries: the executor and, while it waits, why. `null` when there is no line. */
export function jobExecutorHint(job: JobExecutorSource): string | null {
  const line = jobExecutorLine(job);
  if (line === null) return null;
  const wait = jobWaitSentence(line);
  return wait === null ? `${jobExecutorSentence(line)}.` : `${jobExecutorSentence(line)}. ${wait}`;
}
